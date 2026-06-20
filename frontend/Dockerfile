FROM oven/bun:1

WORKDIR /workspace/frontend

ENV HOME=/home/bun \
    BUN_INSTALL_CACHE_DIR=/home/bun/.bun/install/cache

RUN mkdir -p /workspace/frontend/node_modules /home/bun/.bun/install/cache \
    && chmod 0777 /workspace/frontend /workspace/frontend/node_modules /home/bun /home/bun/.bun /home/bun/.bun/install /home/bun/.bun/install/cache
