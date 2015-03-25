CREATE DATABASE `ipy`;

USE `ipy`;

CREATE TABLE `users` (
	`id` int(11) NOT NULL AUTO_INCREMENT, 
	`username` varchar(255) DEFAULT NULL, 
	PRIMARY KEY (`id`)
);

CREATE TABLE `sessions` (
	`id` int(11) NOT NULL AUTO_INCREMENT,
	`user_id` int(11) DEFAULT NULL,
	`port` int(11) DEFAULT NULL,
	`pid` int(11) DEFAULT NULL,
	`updated` int(11) DEFAULT NULL,
	PRIMARY KEY (`id`)
);