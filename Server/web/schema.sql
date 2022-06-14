create table if not exists user
(
    username text
        constraint user_pk primary key,
    email    text not null unique,
    password text not null,
    name     text not null,
    join_at  DATETIME default current_timestamp not null
);
create index if not exists user_login_index ON user (username COLLATE NOCASE, password);

create table if not exists doorbell
(
    id            integer
        constraint doorbell_pk primary key,
    name          text not null,
    owner         text references user on update cascade on delete restrict,
    registered_at DATETIME default current_timestamp not null
);
create index if not exists doorbell_index_owner ON doorbell (owner COLLATE NOCASE);
create index if not exists doorbell_index_id_owner ON doorbell (id, owner COLLATE NOCASE);

create table if not exists alerts
(
    id       integer
        constraint alerts_pk primary key autoincrement,
    uuid     integer not null,
    time     DATETIME default current_timestamp not null,
    type     integer not null,
    checked  boolean  default false not null,
    filename text     default null,
    notes    text     default null
);
create index if not exists alerts_index_uuid ON alerts (uuid);
create index if not exists alerts_index_uuid_check ON alerts (uuid, checked);
create index if not exists alerts_index_uuid_file ON alerts (uuid, filename);
create index if not exists alerts_index_uuid_type ON alerts (uuid, type);
create index if not exists alerts_index_uuid_check_type ON alerts (uuid, checked, type);
create index if not exists alerts_index_uuid_file_type ON alerts (uuid, filename, type);

create table if not exists doorbell_alerts
(
    uuid  integer references doorbell on update cascade on delete cascade,
    email text,
    constraint doorbell_alerts_pk primary key (uuid, email)
);