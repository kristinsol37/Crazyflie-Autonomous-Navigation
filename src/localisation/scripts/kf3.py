#!/usr/bin/env python

import rospy
import tf2_ros
import tf2_geometry_msgs
from geometry_msgs.msg import TransformStamped
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from numpy import dot, sum, tile, linalg, exp, log, pi, diag, eye, zeros, array
from numpy.linalg import inv, det
from numpy.random import randn


class kalman_filter:
    def __init__(self):

        self.first_time = True

        # MOTION MODEL
        # Coefficients of motion variables
        self.A = eye(3)
        # Control from motion model
        self.B = zeros([3, 3])
        self.u = zeros([3, 1])
        # Covariance of motion model
        self.R = eye(3)*0.1

        # MEASUREMENT MODEL
        # Coefficients of measurement variables
        self.C = eye(3) #array([[1, 1, 1]])
        # Covariance of measurement model
        self.Q = 1

        self.mu = None
        self.sigma = None
        self.z = None


        self.pose_sub = rospy.Subscriber('/kf3/input', TransformStamped, self.pose_callback,
                                         queue_size=1, buff_size=2 ** 24)
        self.pub = rospy.Publisher('kf3/output', TransformStamped, queue_size=10)

    def pose_callback(self, msg):
        p, q = self.transform_stamped_to_pq(msg)
        roll, pitch, yaw = euler_from_quaternion(q)
        # Mean of the state: [x, y, yaw]
        self.mu = array([[p[0]], [p[1]], [yaw]])
        # self.mu = array([[2], [3], [4]])
        if self.first_time:
            # Covariance of the state
            self.sigma = eye(3)*0.01
            # Measurment model
            self.z = array([[self.mu[0, 0]],
                             [self.mu[1, 0]],
                             [self.mu[2, 0]]
                            ])
                    #array([self.mu[0, 0],
                    #       self.mu[1, 0],
                    #       self.mu[2, 0]
                    #       ])

        # Estimated belief
        self.mu, self.sigma = self.kf_predict()
        print('after predict')
        print(self.sigma)

        # Posterior distribution and Kalman Gain
        self.mu, self.sigma, K = self.kf_update()
        print('after update')
        print(self.sigma)

        # Measurment model
        self.z = array([[p[0]], [p[1]], [yaw]]) #array([p[0], p[1], yaw])
        # self.z = array([2, 3, 4]) #array([[2], [3], [4]])


        # Update the transform with the updated variables
        msg.transform.translation.x = self.mu[0, 0]  # x
        msg.transform.translation.y = self.mu[1, 0]  # y

        (msg.transform.rotation.x,
         msg.transform.rotation.y,
         msg.transform.rotation.z,
         msg.transform.rotation.w) = quaternion_from_euler(0, 0, self.mu[2, 0])  # yaw

        self.pub.publish(msg)
        self.first_time = False

    def transform_to_pq(self, msg):
        """Convert a C{geometry_msgs/Transform} into position/quaternion np arrays

        @param msg: ROS message to be converted
        @return:
          - p: position as a np.array
          - q: quaternion as a numpy array (order = [x,y,z,w])
        """
        p = array([msg.translation.x, msg.translation.y, msg.translation.z])
        q = array([msg.rotation.x, msg.rotation.y, msg.rotation.z, msg.rotation.w])
        return p, q

    def transform_stamped_to_pq(self, msg):
        """Convert a C{geometry_msgs/TransformStamped} into position/quaternion np arrays

        @param msg: ROS message to be converted
        @return:
          - p: position as a np.array
          - q: quaternion as a numpy array (order = [x,y,z,w])
        """
        return self.transform_to_pq(msg.transform)

    def kf_predict(self):
        # Estimated mean of the state
        mu = dot(self.A, self.mu) + dot(self.B, self.u)

        # Estimated covariance of the state
        sigma = dot(self.A, dot(self.sigma, self.A.T)) + self.R

        return mu, sigma


    def kf_update(self):
        # Kalman Gain
        K_term = dot(self.C.T, 1/(dot(self.C, dot(self.sigma, self.C.T)) + self.Q))
        K = dot(self.sigma, K_term)
        # Innovation
        eta = self.z - dot(self.C, self.mu)

        #print(self.z.shape, K.shape, eta.shape)
        # Compute posterior
        mu = self.mu + dot(K, eta) # Mean of the state
        I = eye(3)
        sigma = dot((I - dot(K, self.C)), self.sigma) # Covariance of the state

        return mu, sigma, K


if __name__ == '__main__':
    print('Starting...')
    print('Ready')

    rospy.init_node('kf3')
    kf = kalman_filter()
    rospy.spin()

