.. _technical-requirements:


Software requirements
=====================
=======================  ==============
Software/framework       Version        
-----------------------  --------------
Python                   3.8
PostgreSQL               9.6+  
Node                     13
=======================  ==============

The current python dependencies can be found in github repository dowc/requirements/production.txt.
The current node dependencies can be found in github repository dowc/package.json.


Hardware requirements
=====================

Currently in our production implementation we have ~50 concurrent users and run the following
kubernetes settings:

=======================  ==============
Resource                 Values        
-----------------------  --------------
DOWC
-----------------------  --------------
CPU: requests            750m             
CPU: limits              750m
Memory: requests         512Mi
Memory: limits           512Mi
Storage                  Persistent 1Gi
Replica count            1-100
Replica autoscale        True
-----------------------  --------------
Redis
-----------------------  --------------
CPU: requests            256m             
CPU: limits              256m
Memory: requests         64Mi
Memory: limits           128Mi
Storage                  Persistent 1Gi
Replica count            1
=======================  ==============
