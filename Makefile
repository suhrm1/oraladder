PYTHON ?= python
VENV   ?= venv
WGET   ?= wget --no-check-certificate

MAP_PACK_VERSION = 2020-12-20
MAP_PACK = ladderweb/static/ladder-map-pack-$(MAP_PACK_VERSION).zip

ACTIVATE = $(VENV)/bin/activate

webdev: initwebdev
	(. $(ACTIVATE) && FLASK_APP=ladderweb FLASK_ENV=development flask run)

initwebdev: $(VENV) $(MAP_PACK)
	mkdir -p instance
	(. $(ACTIVATE) && ora-ladder -d instance/db.sqlite3)

ragldev: initwebdev
	(. $(ACTIVATE) && FLASK_APP=raglweb FLASK_ENV=development flask run)

wheel: $(VENV)
	(. $(ACTIVATE) && pip install wheel && python setup.py bdist_wheel)

maps:
	$(WGET) -i misc/maps_list.txt --continue --content-disposition --directory-prefix $@

mappack: $(MAP_PACK)

$(MAP_PACK): maps
	$(RM) $(MAP_PACK)
	zip -9 -r $(MAP_PACK) $^

clean:
	$(RM) -r build
	$(RM) -r dist
	$(RM) -r maps $(MAP_PACK)
	$(RM) -r oraladder.egg-info
	$(RM) -r venv

$(VENV):
	$(PYTHON) -m venv $@
	( . $(ACTIVATE) && pip install -e .)

.PHONY: webdev initwebdev wheel clean mappack ragldev