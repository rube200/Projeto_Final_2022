create table if not exists user
(
    username text
        constraint user_pk
            primary key,
    email    text not null unique,
    password text not null,
    name     text not null,
    join_at  timestamp default current_timestamp not null
);
create index if not exists user_nocase_username_email ON user (username COLLATE NOCASE, email COLLATE NOCASE);

create table if not exists doorbell
(
    id            integer
        constraint doorbell_pk
            primary key,
    name          text not null,
    owner         text
        references user
            on update cascade on delete restrict,
    registered_at timestamp default current_timestamp not null
);
create index if not exists doorbell_nocase_owner ON doorbell(owner COLLATE NOCASE);

create table if not exists notifications
(
    id      integer
        constraint notifications_pk
            primary key autoincrement,
    uuid    integer not null,
    time    timestamp default current_timestamp not null,
    type    integer not null,
    checked boolean   default false not null,
    path    text
);

create table if not exists doorbell_notifications
(
    uuid  integer
        references doorbell
            on update cascade on delete cascade,
    email text,
    constraint doorbell_notifications_pk
        primary key (uuid, email)
);
create index if not exists doorbell_notifications_nocase_email ON doorbell_notifications (email COLLATE NOCASE);