// ╻ ╻┏━┓┏━╸┏━┓┏━┓
// ┃ ┃┗━┓┣╸ ┣┳┛┗━┓
// ┗━┛┗━┛┗━╸╹┗╸┗━┛

db.pages.drop();

db.pages.ensureIndex({ '_id' : 1, 'timestamp.cache' : 1});
db.pages.ensureIndex({ 'user._id' : 1, 'type' : 1, 'timestamp.cache': 1, '_id' : 1});

site_user = ObjectId('50bb047f17a78f9c422b45da');
shane_user = ObjectId('50bb047f17a78f9c422b45db');
happy_user = ObjectId('50bb047f17a78f9c422b45dd');

db.pages.save({
    '_id': ObjectId('40bb047f17a78f9c422b45da'),
    'timestamps' : {
        'cache': ISODate('2012-02-09T00:30:13.140Z'),
        'login': null,
    },
    'user': {
        '_id': site_user,
    },
    'type': 'about',
    'format': 'markdown',
    'data': 'about me',
});

db.pages.save({
    '_id': ObjectId('41bb047f17a78f9c422b45da'),
    'timestamps' : {
        'cache': ISODate('2012-02-09T00:30:13.140Z'),
        'login': null,
    },
    'user': {
        '_id': site_user,
    },    
    'type': 'site',
    'format': 'markdown',
    'data': 'site page',
});

