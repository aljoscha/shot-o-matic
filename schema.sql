drop table if exists users;
create table users (
  name string unique not null,
  password string not null,
  admin boolean not null,
  screenshots_dir string
);
