#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$ROOT/bin"
mkdir -p "$BIN_DIR"

OS="$(uname -s)"
ARCH="$(uname -m)"
echo "Detected OS=$OS ARCH=$ARCH"

# 1) yt-dlp (standalone)
YTDLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
echo "Downloading yt-dlp..."
curl -L -o "$BIN_DIR/yt-dlp" "$YTDLP_URL"
chmod +x "$BIN_DIR/yt-dlp"
echo "yt-dlp installed to $BIN_DIR/yt-dlp"

# 2) ffmpeg
if [[ "$OS" == "Linux" && ( "$ARCH" == "x86_64" || "$ARCH" == "amd64" ) ]]; then
  echo "Downloading ffmpeg static for Linux x86_64..."
  TMP="$BIN_DIR/ffmpeg-tmp.tar.xz"
  curl -L -o "$TMP" "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  tar -xJf "$TMP" -C "$BIN_DIR"
  rm "$TMP"
  # Normalize dir name
  EXDIR=$(find "$BIN_DIR" -maxdepth 1 -type d -name "ffmpeg-*-static" | head -n1)
  if [ -n "$EXDIR" ]; then
    ln -sf "$(basename "$EXDIR")/ffmpeg" "$BIN_DIR/ffmpeg"
    ln -sf "$(basename "$EXDIR")/ffprobe" "$BIN_DIR/ffprobe"
  fi
  chmod +x "$BIN_DIR/ffmpeg" "$BIN_DIR/ffprobe" || true
elif [[ "$OS" == "Darwin" ]]; then
  echo "Attempting to download macOS ffmpeg (may require manual step)..."
  # Try evermeet (may return zip)
  curl -L -o "$BIN_DIR/ffmpeg.zip" "https://evermeet.cx/ffmpeg/zip"
  unzip -o "$BIN_DIR/ffmpeg.zip" -d "$BIN_DIR"
  rm "$BIN_DIR/ffmpeg.zip"
  chmod +x "$BIN_DIR/ffmpeg" || true
else
  echo "Unsupported OS/ARCH combination: $OS $ARCH. Please provide ffmpeg binary manually into $BIN_DIR"
  exit 1
fi

echo "Portable tools installed into $BIN_DIR"
echo "Remember to include $BIN_DIR in PATH or set FFMPEG_BINARY to $BIN_DIR/ffmpeg"