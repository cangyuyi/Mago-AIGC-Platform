#!/usr/bin/env bash
# Run the repository-pinned pnpm version even when the host has another global version.
set -euo pipefail

PINNED_PNPM_VERSION="${PNPM_VERSION:-9.15.0}"

if command -v corepack >/dev/null 2>&1; then
  exec corepack "pnpm@${PINNED_PNPM_VERSION}" "$@"
fi

if command -v pnpm >/dev/null 2>&1; then
  installed_version="$(pnpm --version 2>/dev/null || true)"
  if [[ "$installed_version" == "$PINNED_PNPM_VERSION" ]]; then
    exec pnpm "$@"
  fi
fi

cat >&2 <<MSG
找不到可用的 pnpm ${PINNED_PNPM_VERSION}。
请安装 Node.js 20+（自带 Corepack），然后重试；也可以手动安装 pnpm ${PINNED_PNPM_VERSION}。
MSG
exit 1
