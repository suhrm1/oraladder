FROM rmoriz/openra

USER root

RUN apt-get update && apt-get upgrade -y && apt-get install -y python3 python3-pip && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY entrypoint.sh /home/openra/lib/openra/
COPY server.sh /home/openra/lib/openra/

RUN chmod +x /home/openra/lib/openra/entrypoint.sh \
    && chmod +x /home/openra/lib/openra/server.sh \
    && chown -R openra: /home/openra/lib/openra/

USER openra

COPY srvwrap_minimal.py /home/openra/lib/openra/

RUN touch /home/openra/banned_profiles

CMD [ "/home/openra/lib/openra/entrypoint.sh" ]
