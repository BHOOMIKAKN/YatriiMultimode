CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255),  -- optional, if you're using login
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wallet (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,  -- Initial balance can be 0 or any value you prefer
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);



CREATE TABLE transport_modes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mode VARCHAR(20) -- bus, train, flight, cab
);

CREATE TABLE routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(100),
    destination VARCHAR(100),
    mode_id INT,
    duration INT, -- in minutes
    cost DECIMAL(10,2),
    departure_time DATETIME,
    arrival_time DATETIME,
    operating_days varchar(50),
    FOREIGN KEY (mode_id) REFERENCES transport_modes(id)
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    route_id INT NOT NULL,
    cost DECIMAL(10, 2) NOT NULL,
    booking_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    confirmation_code VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (route_id) REFERENCES routes(id)
);
CREATE TABLE booking_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    route_id INT NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(id),
    FOREIGN KEY (route_id) REFERENCES routes(id)
);

INSERT INTO transport_modes (mode) VALUES 
('bus'),
('train'),
('flight'),
('cab');
INSERT INTO routes (source, destination, mode_id, duration, cost, departure_time, arrival_time) VALUES
-- Davangere to Bangalore
('Davangere', 'Bangalore', 1, 300, 450.00, '06:00:00', '11:00:00'),
('Davangere', 'Bangalore', 2, 240, 350.00, '07:00:00', '11:00:00'),

-- Bangalore to Delhi
('Bangalore', 'Delhi', 3, 180, 3500.00, ' 13:00:00', ' 16:00:00'),
('Bangalore', 'Delhi', 2, 1500, 1200.00, ' 14:00:00', ' 15:00:00'),

-- Delhi to Srinagar
('Delhi', 'Srinagar', 3, 90, 2000.00, ' 16:00:00', ' 17:30:00'),
('Delhi', 'Srinagar', 2, 900, 950.00, ' 18:00:00', ' 09:00:00'),

-- Srinagar to Kashmir
('Srinagar', 'Kashmir', 1, 120, 300.00, ' 10:00:00', ' 12:00:00'),
('Srinagar', 'Kashmir', 4, 90, 500.00, ' 11:00:00', ' 12:30:00'),

-- Bangalore to Srinagar (direct)
('Bangalore', 'Srinagar', 3, 150, 4000.00, ' 15:00:00', '17:30:00'),

-- Bangalore to Kashmir (rare direct route)
('Bangalore', 'Kashmir', 3, 180, 5000.00, ' 18:00:00', '21:00:00');
INSERT INTO users (name, wallet_balance) VALUES
('Test User', 10000.00);
ALTER TABLE routes 
MODIFY departure_time TIME, 
MODIFY arrival_time TIME;

-- Davangere to major hubs
INSERT INTO routes (source, destination, mode_id, duration, cost, departure_time, arrival_time) VALUES
('Davangere', 'Bangalore', 1, 300, 450, '06:00:00', '11:00:00'),
('Davangere', 'Bangalore', 2, 240, 350, '07:00:00', '11:00:00'),

-- Bangalore to many cities
('Bangalore', 'Delhi', 3, 180, 3500, '13:00:00', '16:00:00'),
('Bangalore', 'Mumbai', 2, 720, 1000, '18:00:00', '06:00:00'),
('Bangalore', 'Chennai', 1, 420, 600, '15:00:00', '22:00:00'),
('Bangalore', 'Hyderabad', 2, 480, 900, '14:00:00', '22:00:00'),
('Bangalore', 'Goa', 3, 90, 2500, '10:00:00', '11:30:00'),

-- Delhi to Srinagar
('Delhi', 'Srinagar', 3, 90, 2000, '16:00:00', '17:30:00'),
('Delhi', 'Srinagar', 2, 900, 950, '18:00:00', '09:00:00'),

-- Srinagar to Kashmir
('Srinagar', 'Kashmir', 1, 120, 300, '10:00:00', '12:00:00'),
('Srinagar', 'Kashmir', 4, 90, 500, '11:00:00', '12:30:00'),

-- Mumbai to others
('Mumbai', 'Delhi', 3, 150, 4000, '10:00:00', '12:30:00'),
('Mumbai', 'Jaipur', 2, 840, 1100, '20:00:00', '10:00:00'),
('Mumbai', 'Goa', 1, 450, 600, '21:00:00', '04:30:00'),

-- Chennai routes
('Chennai', 'Hyderabad', 2, 540, 850, '22:00:00', '07:00:00'),
('Chennai', 'Delhi', 3, 180, 3700, '05:00:00', '08:00:00'),

-- Jaipur to Kashmir via Delhi
('Jaipur', 'Delhi', 2, 300, 450, '12:00:00', '17:00:00'),

-- Pune to Goa
('Pune', 'Goa', 1, 480, 700, '23:00:00', '07:00:00'),

-- Hyderabad to Kashmir via Delhi
('Hyderabad', 'Delhi', 3, 150, 3500, '06:00:00', '08:30:00'),

-- Goa to Bangalore
('Goa', 'Bangalore', 2, 420, 1000, '09:00:00', '16:00:00');
ALTER TABLE routes ADD COLUMN seats_available INT DEFAULT 50;
ALTER TABLE routes ADD COLUMN operating_days VARCHAR(20);
drop table users;
select * from users;
select * from transport_modes;
select * from routes;
select * from wallet;
select * from bookings;
ALTER TABLE routes
DROP COLUMN seats_available;

SELECT b.id, b.user_id, b.cost, b.booking_time, b.confirmation_code, 
       r.source, r.destination, r.departure_time, r.arrival_time
FROM bookings b
JOIN booking_routes br ON b.id = br.booking_id
JOIN routes r ON br.route_id = r.id
WHERE b.user_id = 3;
DESCRIBE routes;

ALTER TABLE routes MODIFY operating_days VARCHAR(255) DEFAULT 'Daily';
UPDATE routes SET operating_days = 'Daily' WHERE mode_id =3 ;
DELETE FROM routes;
SET SQL_SAFE_UPDATES = 0;
update wallet set balance = 200000 where id=1;
