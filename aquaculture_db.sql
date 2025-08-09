-- Drop the database if it exists to ensure a clean slate
DROP DATABASE IF EXISTS `aquaculture_db`;

-- Create the database
CREATE DATABASE `aquaculture_db` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `aquaculture_db`;

--
-- Table structure for table `employees`
--
CREATE TABLE `employees` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `head_quarter` varchar(100) NOT NULL,
  `location` varchar(100) DEFAULT NULL,
  `kms_covered` int(11) DEFAULT 0,
  `role` enum('employee','manager') NOT NULL DEFAULT 'employee',
  `status` enum('active','inactive','deactivated') NOT NULL DEFAULT 'inactive',
  `last_login` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- Add the default manager account
INSERT INTO `employees` (`id`, `username`, `password`, `head_quarter`, `role`) VALUES (1, 'john', '123', 'HQ1', 'manager');

--
-- Table structure for table `farmers`
--
CREATE TABLE `farmers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employee_id` int(11) NOT NULL,
  `farmer_name` varchar(100) NOT NULL,
  `num_of_ponds` int(11) NOT NULL,
  `doc` varchar(100) NOT NULL,
  `contact_details` varchar(100) NOT NULL,
  `products_using` varchar(255) NOT NULL,
  `visit_proof_path` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  CONSTRAINT `farmers_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Table structure for table `sales`
--
CREATE TABLE `sales` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employee_id` int(11) NOT NULL,
  `farmer_id` int(11) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `quantity_sold` int(11) NOT NULL,
  `sale_date` datetime NOT NULL,
  `prescription` text,
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  KEY `farmer_id` (`farmer_id`),
  CONSTRAINT `sales_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`),
  CONSTRAINT `sales_ibfk_2` FOREIGN KEY (`farmer_id`) REFERENCES `farmers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Table structure for table `sales_targets`
--
CREATE TABLE `sales_targets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employee_id` int(11) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `target_quantity` int(11) NOT NULL,
  `month` int(2) NOT NULL,
  `year` int(4) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `target_period` (`employee_id`,`product_name`,`month`,`year`),
  CONSTRAINT `sales_targets_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `daily_routes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employee_id` int(11) NOT NULL,
  `location_segment` varchar(255) NOT NULL,
  `kms_segment` int(11) NOT NULL,
  `entry_time` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  CONSTRAINT `daily_routes_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;