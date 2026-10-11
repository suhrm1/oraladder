
FROM debian:12

RUN apt-get update && apt-get install -y python3 python3-pip wget nano libicu72 && apt-get clean all \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN useradd -m openra

WORKDIR /tmp

ARG OPENRA_MOD="Red-Alert"
ARG RELEASE_VERSION="20250330"
ARG RELEASE_TYPE="release"
ENV MOD="ra"

RUN if [ $RELEASE_TYPE = "release" ]; \
    then APPIMAGE_FILENAME=OpenRA-${OPENRA_MOD}-x86_64.AppImage; \
    else APPIMAGE_FILENAME=OpenRA-${OPENRA_MOD}-${RELEASE_TYPE}-x86_64.AppImage; fi; \
    APPIMAGE_URL=https://github.com/OpenRA/OpenRA/releases/download/${RELEASE_TYPE}-${RELEASE_VERSION}/${APPIMAGE_FILENAME}; \
    wget $APPIMAGE_URL && mv $APPIMAGE_FILENAME OpenRA.AppImage

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
    && touch banned_profiles

RUN mv /tmp/squashfs-root/* /home/openra/

# Make sure everything inside /home/openra is owned by the unprivileged
# "openra" user. This must run AFTER the mv: recent OpenRA AppImages extract
# with owner-only (0700) directories, which the openra user cannot traverse
# if they remain root-owned.
RUN chown -R openra: /home/openra/

# Apply patches to server settings
RUN python3 -c "from srvwrap_minimal import patch; patch()"

USER openra

CMD [ "./entrypoint.sh" ]
