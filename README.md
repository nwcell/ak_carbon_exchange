Aeffect
==================

```
pip install sphinx-doc
pip install tornado greenlet
pip install markdown
pip install python-geohash
pip install progressbar
pip install stripe
pip install tornado-stripe
pip install git+https://github.com/ajdavis/mongo-python-driver.git@motor

apt-get install gdal-bin python-gdal
```

```
Assuming ObjectId('50bb047f17a78f9c422b45db') is a client.

mongo carboneffect --eval 'db.dropDatabase();'; python ./regiontool.py -vvv ~/Downloads/subd.shp SUBD_NAM 50bb047f17a78f9c422b45db
```
