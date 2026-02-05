-- Migration: Add ghl_data JSON field to contacts table
-- This stores the complete GHL contact response for the contact profile page

USE windoorpro;

-- Add ghl_data JSON column to store full GHL contact information
ALTER TABLE contacts 
ADD COLUMN ghl_data JSON NULL AFTER notes;

