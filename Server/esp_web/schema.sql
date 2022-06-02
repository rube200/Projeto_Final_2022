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
create index if not exists user_nocase_owner ON user(username COLLATE NOCASE, email COLLATE NOCASE);

create table if not exists doorbell
(
    id    integer
        constraint doorbell_pk
            primary key,
    name  text not null,
    owner text collate nocase
        references user
            on update cascade on delete restrict
);
create index if not exists doorbell_nocase_owner ON doorbell(owner COLLATE NOCASE);