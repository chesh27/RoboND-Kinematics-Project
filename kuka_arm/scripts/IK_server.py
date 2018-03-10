#!/usr/bin/env python

# Copyright (C) 2017 Electric Movement Inc.
#
# This file is part of Robotic Arm: Pick and Place project for Udacity
# Robotics nano-degree program
#
# All Rights Reserved.

# Author: Harsh Pandya

################# import modules ##########################################
import rospy
import tf
from kuka_arm.srv import *
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from geometry_msgs.msg import Pose
from mpmath import *
from sympy import *

################# Inverse Kinematics function #############################
def handle_calculate_IK(req):
    rospy.loginfo("Received %s eef-poses from the plan" % len(req.poses))
    if len(req.poses) < 1:
        print "No valid poses received"
        return -1
    else:
    ########## Create symbols ############################################
    	alpha0, alpha1, alpha2, alpha3, alpha4, alpha5, alpha6 = symbols('alpha0:7') # twist angle 
    	a0, a1, a2, a3, a4, a5, a6 = symbols('a0:7') #link length 
    	d1, d2, d3, d4, d5, d6, d7 = symbols('d1:8') # link offset
    	q1, q2, q3, q4, q5, q6, q7 = symbols('q1:8') # joint angle symbols (thetas)
    
    #### Create Modified DH parameters ###################################
    #### A dictionary of our known DH parameter values ###################
    	DH_table = {alpha0:     0, a0: 0    , d1: 0.75 , q1: q1,
              alpha1: -pi/2, a1: 0.35 , d2: 0    , q2: q2-pi/2,
              alpha2:     0, a2: 1.25 , d3: 0    , q3: q3,
              alpha3: -pi/2, a3:-0.054, d4: 1.5  , q4: q4,
              alpha4:  pi/2, a4: 0    , d5: 0    , q5: q5,
              alpha5: -pi/2, a5: 0    , d6: 0    , q6: q6,
              alpha6:     0, a6: 0    , d7: 0.303, q7:  0}

    ##### Define Modified DH Transformation matrix ########################
        def TF_Matrix(a, alpha, d, q):
            TF = Matrix([[           cos(q),           -sin(q),           0,             a],
                        [sin(q)*cos(alpha), cos(q)*cos(alpha), -sin(alpha), -sin(alpha)*d],
                        [sin(q)*sin(alpha), cos(q)*sin(alpha),  cos(alpha),  cos(alpha)*d],
                        [                0,                 0,           0,             1]])
            return TF

    #### Create individual transformation matrices ############################
        T0_1 = TF_Matrix(a0, alpha0, d1, q1).subs(DH_table)
        T1_2 = TF_Matrix(a1, alpha1, d2, q2).subs(DH_table)
        T2_3 = TF_Matrix(a2, alpha2, d3, q3).subs(DH_table)
        T3_4 = TF_Matrix(a3, alpha3, d4, q4).subs(DH_table)
        T4_5 = TF_Matrix(a4, alpha4, d5, q5).subs(DH_table)
        T5_6 = TF_Matrix(a5, alpha5, d6, q6).subs(DH_table)
        T6_G = TF_Matrix(a6, alpha6, d7, q7).subs(DH_table)
    
    #### Composition of Homogenous transforms 
        #T0_2 = simplify(T0_1 * T1_2) #base link to link 2
        #T0_3 = simplify(T0_2 * T2_3) #base link to link 3
        #T0_4 = simplify(T0_3 * T3_4) #base link to link 4
        #T0_5 = simplify(T0_4 * T4_5) #base link to link 5
        #T0_6 = simplify(T0_5 * T5_6) #base link to link 6
        #T0_G = simplify(T0_6 * T6_G) #base link to gripper 

    #### Correction needed to account for orientation difference between definition of gripper link in URDF versis DH convention 
        #R_z = Matrix([[cos(np.pi), -sin(np.pi), 0, 0],
         #              [sin(np.pi), cos(np.pi), 0, 0],
          #              [0, 0, 1, 0],
           #              [0, 0, 0, 1]])
        #R_y = Matrix([[cos(-np.pi/2), 0, sin(-np.pi/2), 0],
         #              [0, 1, 0, 0],
          #              [-sin(-np.pi/2), 0, cos(-np.pi/2), 0],
           #             [0, 0, 0, 1]])
        #R_corr = simplify(R_z * R_y)
    
     #### Total Homogenous Transform between base and Gripper with correction 
        #T_total = simplify(T0_G * R_corr)


    ###########  FORWARD KINEMATICS ENDS  ##############

    #### Initialize service response ##########################################
        joint_trajectory_list = []
        prior_solution = None
        for x in xrange(0, len(req.poses)):
            ## IK code starts here ############################################
            joint_trajectory_point = JointTrajectoryPoint()


	    ### Extract End effector position and orientation from request ####
	    ### px,py,pz represents the end-effector position #################
	    ### roll, pitch, yaw represents end-effector orientation ##########
            px = req.poses[x].position.x
            py = req.poses[x].position.y
            pz = req.poses[x].position.z

            (roll, pitch, yaw) = tf.transformations.euler_from_quaternion(
                [req.poses[x].orientation.x, req.poses[x].orientation.y,
                    req.poses[x].orientation.z, req.poses[x].orientation.w])
    
	    # Compensate matrix for rotation discrepancy between DH parameters and Gazebo #########
          
            r, p, y = symbols('r p y')
            ROT_x = Matrix([[ 1,      0,       0],  ####### ROLL
                            [ 0, cos(r), -sin(r)],
                            [ 0, sin(r),  cos(r)]])
            ROT_y = Matrix([[  cos(p), 0, sin(p)],  ####### PITCH 
                            [ 0, 	 	1,      0],
                            [ -sin(p), 0, cos(p)]])
            ROT_z = Matrix([[ cos(y), -sin(y), 0],  ####### YAW 
                            [ sin(y),  cos(y), 0],
                            [      0,       0, 1]])

            ROT_EE = ROT_z * ROT_y * ROT_x  ### URDF coordinates
            ROT_error = ROT_z.subs(y, radians(180)) * ROT_y.subs(p, radians(-90))

            ROT_EE = ROT_EE * ROT_error             ####### corrected to DH coordinate
            ROT_EE = ROT_EE.subs({'r': roll, 'p': pitch, 'y': yaw})

            ############# Position of End-Effector #########################################
            EE = Matrix([[px],[py],[pz]])
            
            ############# Wrist Center (walkthrough / Inverse kinematics section ) #################
            WC = EE - (0.303) * ROT_EE[:,2]

            ############# Theta1 - theta3 can be solved using geometric IK method ##########
            theta1 = atan2(WC[1], WC[0])

            ############# Solve theta 2 and theta 3 using SSS, see supporting visuals ######
            m = sqrt(WC[0]*WC[0] + WC[1]*WC[1]) - 0.35  
            v = WC[2] - 0.75                            

            side_a = 1.501 			  # accounting for -0.054 offset 
            side_b = sqrt(v*v + m*m)              # right triangle 
            side_c = 1.25                         # a2


            ########### Link3 - link4 offset ##############################################
            offset3 = atan2(0.054, 1.5)             

            # Using SSS and cos law, I can now find theta 2 and theta 3
            cos_3 = (-side_a*side_a - side_c*side_c + side_b*side_b) / (2. * side_a * side_c)
            sin3 = sqrt(1 - cos_3*cos_3)

            # There are four possible solutions, as shown in lecture 
            # Iterate through each possible solution and delete those that fall outside the angle limits 
            solutions = []
            for sin_3 in [sin3,-sin3]:
                theta2 = pi/2 -  atan2(side_a*sin_3, side_a*cos_3+side_c) - atan2(v,m)
                theta3 = atan2(sin_3, cos_3) - offset3 - pi/2
                
                # If solution exceeds joint limits, omit it and move on ###################
                if (theta2 < 0 and theta2 < radians(-45)) or (theta2 > 0 and theta2 > radians(85)):
                    continue
                if (theta3 < 0 and theta3 < radians(-210)) or (theta3 > 0 and theta3 > radians(65)):
                    continue

                ######## Composite rotation between theta4 - theta6 ##############################
                R0_3 = T0_1[0:3,0:3] * T1_2[0:3,0:3] * T2_3[0:3,0:3]
                R0_3 = R0_3.evalf(subs={q1:theta1, q2: theta2, q3: theta3})

                ######## NOTE: for orthonormal matrix, inverse matrix = transpose matrix #########
                R3_6 = R0_3.T * ROT_EE
                sin5 = sqrt(R3_6[0,2]*R3_6[0,2] + R3_6[2,2]*R3_6[2,2])
                for sin_5 in [sin5,-sin5]:
                    ###### Solve theta4 - theta6 by euler rotation matrix ######################
                    theta4 = atan2(R3_6[2,2]*sign(sin_5), -R3_6[0,2]*sign(sin_5))
                    theta5 = atan2(sin_5, R3_6[1,2])
                    theta6 = atan2(-R3_6[1,1]*sign(sin_5), R3_6[1,0]*sign(sin_5))

                    ######## Again, if solution exceeds joint limits, omit it ##################
                    if (theta5 < 0 and theta5 < radians(125)) or (theta5 > 0 and theta5 > radians(125)):
                        continue
                    solutions.append([theta1, theta2, theta3, theta4, theta5, theta6])

            if prior_solution is None:
                theta1, theta2, theta3, theta4, theta5, theta6 = solutions[0][:]
            else:
                # Next solution is selected based on the valid angle (within the limits shown in urdf) and also that which is at the minimum distance from the prior solution. this will try to get rid of any jerky motions 
                
                minimum_solution = None
                minimum_cost = 99999999.
                for solution in solutions:
                    cost = 0.
                    for i, theta in enumerate(solution):
                        cost += abs(theta - prior_solution[i])
                    if minimum_solution is None or cost < minimum_cost:
                        minimum_solution = solution
                        minimum_cost = cost
                        theta1, theta2, theta3, theta4, theta5, theta6 = minimum_solution[:]
		
            ################ Populate response for the IK request ############################
	    joint_trajectory_point.positions = prior_solution = \
                    [theta1, theta2, theta3, theta4, theta5, theta6]
	    joint_trajectory_list.append(joint_trajectory_point)

        rospy.loginfo("length of Joint Trajectory List: %s" % len(joint_trajectory_list))
        return CalculateIKResponse(joint_trajectory_list)


def IK_server():
    ############3 initialize node and declare calculate_ik service ##########################
    rospy.init_node('IK_server')
    s = rospy.Service('calculate_ik', CalculateIK, handle_calculate_IK)
    print "Ready to receive an IK request"
    rospy.spin()

if __name__ == "__main__":
    IK_server()