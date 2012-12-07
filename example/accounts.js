// ╻ ╻┏━┓┏━╸┏━┓┏━┓
// ┃ ┃┗━┓┣╸ ┣┳┛┗━┓
// ┗━┛┗━┛┗━╸╹┗╸┗━┛

db.users.drop();

db.users.ensureIndex({ '_id' : 1, 'timestamp.cache' : 1});
db.users.ensureIndex({ 'email' : 1, 'password' : 1, '_id' : 1});

site_user = ObjectId('50bb047f17a78f9c422b45da');
shane_user = ObjectId('50bb047f17a78f9c422b45db');
happy_user = ObjectId('50bb047f17a78f9c422b45dc');

db.users.save({
    '_id': site_user,
    'timestamps' : {
        'joined': ISODate("2012-02-09T00:30:13.140Z"),
        'login': null,
        'cache': ISODate("2012-02-09T00:30:13.140Z"),
    },
    'email': 'webmaster@akcarbonexchange.com',
    'name': {
        'first': 'Web',
        'last': 'Master',         
        'preferred': 'Alaska Carbon Echange',
    },
    'password': '$2a$10$1EztV8icBkB0SflToXIT0uSPbu/YFAC/1wlEBw.6nZFxNDU8jc3N6',
    'timezone': 'America/Anchorage',
    'content': {
        'blogs': { // redundant to db.blogs.. just summary information
            'default': {
                'active': false,                
                'name': 'The Alaska Carbon Exchange Blog',
                'posts': [],
            },
        },
        'pages': {
            'about': {
                '_id': ObjectId('40bb047f17a78f9c422b45da'),
                'cache': null,
            },
            'site': {
                '_id': ObjectId('41bb047f17a78f9c422b45da'),
                'cache': null,
            },
        },
    },
    'inbounder': 'webmaster',
    'regions': [],
});

db.users.save({
    '_id': shane_user,
    'timestamps' : {
        'joined': ISODate("2012-02-09T00:30:13.140Z"),
        'login': null,
        'cache': ISODate("2012-02-09T00:30:13.140Z"),
    },
    'email': 'shane@bogomip.com',
    'name': {
        'first': 'Shane',
        'last': 'Spencer',         
        'preferred': 'Shane R. Spencer',
    },
    'password': '$2a$10$1EztV8icBkB0SflToXIT0uSPbu/YFAC/1wlEBw.6nZFxNDU8jc3N6',
    'timezone': 'America/Anchorage',
    'content': {
        'blogs': { // redundant to db.blogs.. just summary information
            'default': {
                'active': false,                
                'name': 'Shane R. Spencers\'s Blog',
                'posts': [],
            },
        },
    },
    'inbounder': 'shanespencer',
    'regions': [],
});

db.users.save({
    '_id': shane_user,
    'timestamps' : {
        'joined': ISODate("2012-02-09T00:30:13.140Z"),
        'login': null,
        'cache': ISODate("2012-02-09T00:30:13.140Z"),
    },
    'email': 'happy@example.com',
    'name': {
        'first': 'James',
        'last': 'Hapner',         
        'preferred': 'James (Happy) Hapner Jr.',
    },
    'password': '$2a$12$ksdmmbBX2kVhY/aONAd7Ye.1ZfPOe0u2IRnuHz1PwAyWjeS9oWhme',
    'timezone': 'America/Anchorage',
    'content': {
        'blogs': {
            'default': {
                'active': false,                
                'name': 'James (Happy) Hapner\'s Blog',
                'posts': [],
            },
        },
    },
    'inbounder': 'mrhappy',
    'regions': [],
});

