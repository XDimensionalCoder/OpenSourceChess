@echo off
echo Merhaba. Satranç'ta yeteneklerini görüp denemek için birkaç adım göstericeğiz.
ping 127.0.0.1 -t 3
echo İlk önce derlemeyi indirin indirmediyseniz...
ping 127.0.0.1 -t 2
py -m pip install python-chess pygame
echo İndirildi. 
