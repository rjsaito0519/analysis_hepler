#!/bin/sh

VAR=`LC_ALL=C date`
git add .
git commit -m "$VAR"
git push origin main