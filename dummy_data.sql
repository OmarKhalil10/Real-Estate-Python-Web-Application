USE arram;

INSERT INTO employees (name, id_number, phone, date_of_birth, address, qualifications, job_title) VALUES
('Ashraf Arram', '300210105120','+20 120 5310 694', '1984-07-04', 'New Cairo', 'Bachelor Degree in Linguistics', 'General Manager'),
('Samaa Jad', '300210105120','+20 120 5310 694', '1998-10-04', 'New Cairo', 'Bachelor Degree in Linguistics', 'Human Resources Specialist'),
('John Aziz', '300210105120','+20 120 5310 694', '2000-10-03', 'New Cairo', 'Bachelor Degree in Linguistics', 'Technical Consultant'),
('Wally Allam', '300210105120','+20 120 5310 694', '1997-07-05', 'New Cairo','Bachelor Degree in Linguistics', 'Sales Representative');
('Salma Hany', '300210105120','+20 120 5310 694', '1997-07-05', 'New Cairo','Bachelor Degree in Linguistics', 'Admin');

INSERT INTO employees (name, id_number, phone, date_of_birth, address, qualifications, job_title) VALUES
('Ashraf Arram', '300210105120','+20 120 5310 694', '1984-07-04', 'New Cairo', 'Bachelor Degree in Linguistics', 'General Manager'),
('Samaa Jad', '300210105120','+20 120 5310 694', '1998-10-04', 'New Cairo', 'Bachelor Degree in Linguistics', 'Human Resources Specialist'),
('John Aziz', '300210105120','+20 120 5310 694', '2000-10-03', 'New Cairo', 'Bachelor Degree in Linguistics', 'Technical Consultant'),
('Wally Allam', '300210105120','+20 120 5310 694', '1997-07-05', 'New Cairo','Bachelor Degree in Linguistics', 'Sales Representative');
('Salma Hany', '300210105120','+20 120 5310 694', '1997-07-05', 'New Cairo','Bachelor Degree in Linguistics', 'Admin');

INSERT INTO salaries (salary, employees_id) VALUES
(0, 1),
(4000, 2),
(4000, 3),
(4000, 4),
(4000, 5),
(4000, 6),
(4000, 7),
(4000, 8),
(4000, 9),
(4000, 10);


INSERT INTO credential (username, password, role, employees_id) VALUES
('arram@arram-group.com', 'sha256$jWf05K4YPARXHspc$51de475c21f7c516777b9ad2121b5bf97f427116cb3d9dd2f7207f46a7e75e6b','gm', 1);
INSERT INTO credential (username, password, role,employees_id, salaries_id) VALUES
('samaa@arram-group.com', 'sha256$FSfhz3dURbVJodmV$a4279ce265dd9ff896f587bcc603b19075af4835258142ee65eef9b944f78d02','hr', 2, 1),
('john@arram-group.com', 'sha256$EFd4hrbFlsbca1OF$86dfcc4cc8efecb5302f8e959460b3a53600b8f6855be98748b2f57c8b4a0a69', 'it', 3 , 2),
('wally@arram-group.com', 'sha256$Hx1xRihqabFwTIz7$358b2fc20e507c26ea6278042939164228210fc6ace0de33e88f7e1b84a1b6f7','sales',4, 3);

INSERT INTO deals (created_time, buyer_name, phone, assigned_to, status, project_developer, project_name, project_type, description, unit_price, commission, email, down_payment) VALUES
('2021-08-09', 'Ahmed Mohamed', '+20 120 531 0694', 4, 'Visited', 'اعمار', 'العاصمة الادارية', 'سكني', 'قاللي هيشتري قريب', 400000, '5%', 'johnaziz@gmail.com' , 10000);

INSERT INTO description (created_time, description, employees_id, leads_id, deals_id) VALUES
('2021-08-09', 'قاللي هيشتري قريب', 4, 1, null);


INSERT INTO leads (created_time, client_name, phone, email, assigned_to, status, request, channel, description) VALUES
('2021-08-09', 'Ahmed Mohsen', '+20 120 478 0694','mohsenmeme@gmail.com', 4, 'Visited', 'عميل جديد', 'Facebook', 'Villa');


UPDATE credential 
SET 
    password='pbkdf2:sha256:260000$YWJUSddVceRTTi4v$9788a2876c9a42be2bfca22ddc3b78b031fd5d3799a0907c7897f2a033f8c516'
WHERE 
    id = 1;

UPDATE credential 
SET 
    password='pbkdf2:sha256:260000$XieFLlwZ84VEzUdv$9aa502ab0fef1471b3fbb75309590734032bab6225e63f5f4148f4eab065f53b'
WHERE 
    id = 2;

UPDATE credential 
SET 
    password='pbkdf2:sha256:260000$MKJy8MOUOCsyVjQ7$cf3a0861bb4a85420d683bde2bcf8ae2d362a2c5fb624045a05168a7e46ff7dc'
WHERE 
    id = 3;

UPDATE credential 
SET 
    password='pbkdf2:sha256:260000$ilBSDOnnhBlwxDwG$b5dcf00839778c288511303d62ac2a2bf6b944da0159092e1b1d4b8e7cac2b30'
WHERE 
    id = 4;
