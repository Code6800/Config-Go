-- Migration: Add 'user' role to team_members table
-- Run this if your database already exists and doesn't have the 'user' role

USE windoorpro;

-- Alter the role ENUM to include 'user'
ALTER TABLE team_members 
MODIFY COLUMN role ENUM('admin', 'user', 'sales', 'manager') DEFAULT 'user';

