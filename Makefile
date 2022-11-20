PYTHON ?= python3
CURL   ?= curl
VENV   ?= venv

RAGL_MAP_POOL = misc/map-pools/ragl-s12.maps
RAGL_MAP_PACK_VERSION := $(shell $(PYTHON) misc/ragl_config.py MAP_PACK_VERSION)
RAGL_MAP_PACK = raglweb/static/ragl-map-pack-$(RAGL_MAP_PACK_VERSION).zip

TDGL_MAP_POOL = misc/map-pools/tdgl-s03.maps
TDGL_MAP_PACK_VERSION := $(shell $(PYTHON) misc/tdgl_config.py MAP_PACK_VERSION)
TDGL_MAP_PACK = raglweb/static/tdgl-map-pack-$(TDGL_MAP_PACK_VERSION).zip

LADDER_STATIC = ladderweb/static/Chart.bundle.min.js  \
                ladderweb/static/Chart.min.css        \
                ladderweb/static/datatables.min.js    \
                ladderweb/static/jquery.min.js        \

LADDER_DATABASES = instance/db-ra-all.sqlite3 \
                   instance/db-ra-2m.sqlite3  \
                   instance/db-td-all.sqlite3 \
                   instance/db-td-2m.sqlite3  \

# https://github.com/chartjs/Chart.js/releases/latest
CHART_JS_VERSION = 2.9.3

# https://github.com/jquery/jquery/releases/latest
JQUERY_VERSION = 3.6.0

# https://github.com/DataTables/DataTables/releases/latest
DATATABLES_VERSION = 1.10.24

ladderdev: initladderdev
	FLASK_APP=ladderweb FLASK_DEBUG=True FLASK_RUN_PORT=5000 $(VENV)/bin/flask run

initladderdev: $(VENV) $(LADDER_STATIC) $(LADDER_DATABASES)

ladderweb/static/Chart.min.css:
	$(CURL) -L https://cdnjs.cloudflare.com/ajax/libs/Chart.js/$(CHART_JS_VERSION)/Chart.min.css -o $@

ladderweb/static/Chart.bundle.min.js:
	$(CURL) -L https://cdnjs.cloudflare.com/ajax/libs/Chart.js/$(CHART_JS_VERSION)/Chart.bundle.min.js -o $@

ladderweb/static/datatables.min.js:
	$(CURL) -L https://cdn.datatables.net/v/dt/dt-$(DATATABLES_VERSION)/datatables.min.js -o $@

ladderweb/static/jquery.min.js:
	$(CURL) -L https://code.jquery.com/jquery-$(JQUERY_VERSION).min.js -o $@

$(LADDER_DATABASES): instance
	([ -f $@ ] ||  $(VENV)/bin/ora-ladder -d $@)

ragldev: initragldev
	FLASK_APP=raglweb FLASK_DEBUG=True FLASK_RUN_PORT=5001 RAGLWEB_DATABASE="db-ragl.sqlite3" $(VENV)/bin/flask run

tdgldev: inittdgldev
	FLASK_APP=raglweb FLASK_DEBUG=True FLASK_RUN_PORT=5001 RAGLWEB_DATABASE="db-tdgl.sqlite3" RAGL_CONFIG=../instance/tdgl_config.py $(VENV)/bin/flask run

initragldev: $(VENV) $(RAGL_MAP_PACK) instance/db-ragl.sqlite3 instance/ragl_config.py

inittdgldev: $(VENV) $(TDGL_MAP_PACK) instance/db-tdgl.sqlite3 instance/tdgl_config.py

instance/db-ragl.sqlite3: instance
	$(VENV)/bin/ora-ragl -d $@

instance/db-tdgl.sqlite3: instance
	$(VENV)/bin/ora-ragl -d $@ -p ../oraladder/laddertools/tdgl-s03.yml

instance/ragl_config.py: misc/ragl_config.py instance
	cp $< $@

instance/tdgl_config.py: misc/tdgl_config.py instance
	cp $< $@

instance:
	mkdir -p $@

wheel: $(VENV) mappacks
	$(VENV)/bin/python -m pip install wheel && python setup.py bdist_wheel

mappacks: $(RAGL_MAP_PACK)

$(RAGL_MAP_PACK): $(VENV)
	$(VENV)/bin/ora-mapstool $(RAGL_MAP_POOL) --pack $(RAGL_MAP_PACK)

$(TDGL_MAP_PACK): $(VENV)
	$(VENV)/bin/ora-mapstool $(TDGL_MAP_POOL) --pack $(TDGL_MAP_PACK)

test: $(VENV)
	$(VENV)/bin/pytest -v

clean:
	$(RM) -r build
	$(RM) -r dist
	$(RM) -r $(RAGL_MAP_PACK)
	$(RM) -r oraladder.egg-info
	$(RM) -r venv

$(VENV):
	$(PYTHON) -m venv $@
	$(VENV)/bin/python -m pip install -e .

.PHONY: ladderdev initladderdev wheel clean mappacks ragldev initragldev test
