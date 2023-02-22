FROM debian:latest

RUN apt-get update && apt-get install -y python3 python3-pip wget nano libicu67 && apt-get clean all \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN useradd -m openra

WORKDIR /tmp

ARG OPENRA_MOD="Red-Alert"
ARG RELEASE_VERSION="20230218"
ARG RELEASE_TYPE="playtest"
ENV MOD="ra"

ENV APPIMAGE_FILENAME=OpenRA-${OPENRA_MOD}-${RELEASE_TYPE}-x86_64.AppImage
ENV APPIMAGE_URL=https://github.com/OpenRA/OpenRA/releases/download/${RELEASE_TYPE}-${RELEASE_VERSION}/${APPIMAGE_FILENAME}

RUN wget $APPIMAGE_URL && mv $APPIMAGE_FILENAME OpenRA.AppImage

# Workaround for AppImages not running in Docker
# see https://github.com/AppImage/AppImageKit/issues/828
RUN dd if=/dev/zero bs=1 count=3 seek=8 conv=notrunc of=OpenRA.AppImage

RUN chmod +x OpenRA.AppImage \
    && ./OpenRA.AppImage --appimage-extract \
    && rm OpenRA.AppImage

WORKDIR /home/openra

COPY entrypoint.sh .
COPY server.sh .
COPY srvwrap_minimal.py .

RUN chmod +x entrypoint.sh \
    && chmod +x server.sh \
    && touch banned_profiles \
    && chown -R openra: /home/openra/

RUN mv /tmp/squashfs-root/* /home/openra/

# Apply patches to server settings
RUN python3 -c "from srvwrap_minimal import patch; patch()"

USER openra

CMD [ "./entrypoint.sh" ]
