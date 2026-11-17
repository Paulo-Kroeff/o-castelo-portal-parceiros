#!/bin/sh
set -eu

mkdir -p portal-public/assets
cp dist/styles.css dist/partner-login.css dist/manifest.webmanifest dist/sw.js portal-public/
cp dist/assets/icon-192.png dist/assets/icon-512.png \
  dist/assets/12Fw7rfB6u47WnVpw5K6mamMKQyNY7wfW.svg \
  dist/assets/1aiUPLwiyj7JUAOPa75_Ss3-GwQ7Ib0LN.webp portal-public/assets/
