# OSPF & BGP Network Simulation System

A web-based network routing simulation platform built using Django that demonstrates the working of dynamic routing protocols such as OSPF (Open Shortest Path First) and BGP (Border Gateway Protocol). The project allows users to simulate routing behavior, visualize path selection, and understand how routers exchange routing information in modern networks.

---

# Features

* OSPF routing simulation
* BGP routing simulation
* Dynamic route calculation
* Interactive network topology visualization
* Shortest path computation
* Autonomous System (AS) based routing
* Router and link configuration support
* Django-powered backend architecture
* Responsive web interface

---

# Tech Stack

## Backend

* Django
* Python

## Frontend

* HTML
* CSS
* JavaScript

## Database

* SQLite (default Django database)

---

# Project Overview

This project simulates how routers communicate and exchange routing information using OSPF and BGP protocols.

## OSPF Simulation

The OSPF module focuses on intra-domain routing. It computes the shortest available path between routers using link-state information and shortest path algorithms.

Key concepts demonstrated:

* Link-state advertisements
* Cost-based routing
* Dijkstra’s shortest path algorithm
* Neighbor discovery
* Routing table generation

## BGP Simulation

The BGP module focuses on inter-domain routing between autonomous systems.

Key concepts demonstrated:

* Path vector routing
* AS path selection
* Route propagation
* Policy-based routing behavior
* External routing communication

---

# System Architecture

```text
User Interface
      ↓
Django Views & Routing Logic
      ↓
OSPF / BGP Simulation Engine
      ↓
Routing Computation Algorithms
      ↓
Database & Topology Storage
```

---

# Installation

## Clone the Repository

```bash
git clone https://github.com/apekshaayy/ospf-bgp-sim.git
cd your-repository-name
```

## Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

#### Windows

```bash
venv\Scripts\activate
```

#### macOS/Linux

```bash
source venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Run Database Migrations

```bash
python manage.py migrate
```

---

# Start the Development Server

```bash
python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

---

# Usage

1. Create routers and define links between them.
2. Configure routing parameters.
3. Select OSPF or BGP simulation mode.
4. Run the simulation.
5. Observe route calculations and topology updates.
6. Analyze shortest paths and routing behavior.

---

# Algorithms Used

## OSPF

* Dijkstra’s Algorithm
* Link-State Routing

## BGP

* Path Vector Algorithm
* AS Path Selection

---

# Learning Outcomes

This project helps in understanding:

* Computer networking fundamentals under my CS402 course at Inidan Institute of Information Technology, Surat
* Routing protocols
* Dynamic routing behavior
* Network topology design
* Distributed communication concepts
* Backend system architecture
* Web-based simulation systems

---

# Future Improvements

* Network traffic visualization
* Router failure simulation
* Multi-user topology collaboration
* Docker deployment
* REST API integration
* Advanced routing metrics
* Dark mode UI
* Live topology editing

---

# Deployment

## Frontend & Django Deployment

This project can be deployed using platforms such as:

* Vercel (frontend/static deployment)
* Render
* Railway
* AWS EC2

For Django deployment, configure:

* Allowed hosts
* Static files
* Environment variables
* Production database
* WSGI server


---

# Author

Apekshaa Yadav

---

# License

This project is created for educational and learning purposes.
