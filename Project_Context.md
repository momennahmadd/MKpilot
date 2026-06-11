Project Context:
I am working on Drive Care 360: a contextual safety layer that fuses openpilot/comma4 forward-road perception with in-cabin sensing to generate adaptive alerts, not self-driving actuation

I have used comma 4 for 3 months with in-cabin radar for CPD/OCPC and modified this repository logging so the device records continously as long as it has power and data is saved and later extracted via SSH. The radar is now discontinoued, and the work in cpd_viewer and cpd_detector is probably not going to be used, therefore i want to repurpose comma 4 as the MVP sensing platform for Drive Care 360.

Goal:
Use comma 4/openpilot passively, without enabling self-driving controls, to extract available perception/context data such as road camera outputs, lead vehicle state, FCW/LDW-related events, driver monitoring/gaze/distraction signals, CAN/speed, GPS/IMU, and any accessible model outputs.

Main Task:
Help me inspect this repository and identify where these signals are produced, published, logged, and how to subscribe to them for a seperate Context AI layer that generates smart alerts