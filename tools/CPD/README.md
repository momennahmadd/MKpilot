#This folder is for the CPD Detector Function
The file cpd_detector.py takes in rlog files decodes them and produced a csv file of the detected instances.

The instances detected are when the state in the FR, FL, RR, RL, RC, FOOT or ALL got from Child (2) to any other state and vice versa.

The instances are logged as:
1,2026-04-15 11:24:23.152,segment1.rlog,RL,ENTER_CHILD,0,2,Empty,Child,
2,2026-04-15 11:25:10.387,segment2.rlog,RL,EXIT_CHILD,2,0,Child,Empty,47.235
3,2026-04-15 11:26:02.912,segment3.rlog,FR,ENTER_CHILD,1,2,Adult,Child,

This enables us to track the instances, view them through CABANA recordings and label them correctly as TP, FP, TN or FN and retrain.