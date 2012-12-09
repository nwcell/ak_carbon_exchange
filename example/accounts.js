// ╻ ╻┏━┓┏━╸┏━┓┏━┓
// ┃ ┃┗━┓┣╸ ┣┳┛┗━┓
// ┗━┛┗━┛┗━╸╹┗╸┗━┛

db.users.drop();

db.users.ensureIndex({ '_id' : 1, 'timestamp.cache' : 1});
db.users.ensureIndex({ 'email' : 1, 'password' : 1, '_id' : 1});

site_user = ObjectId('50bb047f17a78f9c422b45da');
shane_user = ObjectId('50bb047f17a78f9c422b45db');
travis_user = ObjectId('50bb047f17a78f9c422b45dc');

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
    'password': '$2a$12$ipPbwv2IVefxAjasXlcU9OsydLsrcGe5hlwwwe2SLtxEA/ED4LOya', //ace
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
    '_id': travis_user,
    'timestamps' : {
        'joined': ISODate("2012-02-09T00:30:13.140Z"),
        'login': null,
        'cache': ISODate("2012-02-09T00:30:13.140Z"),
    },
    'email': 'travis@example.com',
    'name': {
        'first': 'Travis',
        'last': 'Krause',         
        'preferred': 'Travis (Cheers) Krause',
    },
    'password': '$2a$12$fhilfurQd4avDaO4QfsLwe5cqmFIMxMs3qt8hi83bVIKnnbzvYCRC', // cheers
    'timezone': 'America/Anchorage',
    'content': {
        'blogs': {
            'default': {
                'active': false,                
                'name': 'James (travis) Hapner\'s Blog',
                'posts': [],
            },
        },
    },
    'inbounder': 'mrtravis',
    'regions': [],
});

