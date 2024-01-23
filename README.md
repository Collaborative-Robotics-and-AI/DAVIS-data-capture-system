# DAVIS Data Capture System

Event-based data are known to be a lightweight data format for conveying visual information and well-suited for real-time detection and analysis of human motion.  
However, reliable and easy to use methods for creating event-based datasets are not readily available.

This repository features custom-built Python code to aid researchers to capture DAVIS240C samples for an event-based dataset.
The repository requires the use of external software, namely the jAER open-source software, designed to display and record event data. The Python code interfaces with the jAER software by sending it commands through a UDP connection to start and stop logging data. It also makes use of an Arduino connected through a serial connection to trigger these commands to start and end the recordings.

All data are captured in raw form (.aedat) and can processed into numpy arrays for ease of use (.npy). 
