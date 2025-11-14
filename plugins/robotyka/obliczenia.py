import numpy as np
from scipy.linalg import pinv, inv
from scipy.spatial.transform import Rotation as R

# --- pomocnicze: przekształcenie DH do 4x4 ---
def dh_transform(a, alpha, d, theta):
    ca = np.cos(alpha); sa = np.sin(alpha)
    ct = np.cos(theta); st = np.sin(theta)
    return np.array([
        [ct,     -st*ca,  st*sa, a*ct],
        [st,      ct*ca, -ct*sa, a*st],
        [0.0,     sa,     ca,    d   ],
        [0.0,     0.0,    0.0,   1.0 ]
    ], dtype=float)

# DH table: lista elementów (a, alpha, d, theta, joint_type)
# joint_type: 'R' - revolute (theta is variable), 'P' - prismatic (d is variable)
# theta/d in table are current values (initial guess)
# Example: dh = [(a, alpha, d, theta, 'R'), ...]
def forward_kinematics(dh):
    T = np.eye(4)
    Ts = [T.copy()]  # base frame
    for (a, alpha, d, theta, jtype) in dh:
        t = theta if jtype == 'R' else theta
        dd = d if jtype == 'P' else d
        A = dh_transform(a, alpha, dd, t)
        T = T @ A
        Ts.append(T.copy())
    return T, Ts  # end-effector transform, list of transforms up to each joint

# Jacobian (6 x n)
def compute_jacobian(dh):
    _, Ts = forward_kinematics(dh)
    n = len(dh)
    J = np.zeros((6, n))
    o_n = Ts[-1][:3, 3]
    for i in range(n):
        T_i = Ts[i]
        z = T_i[:3, 2]   # z_{i} (axis of joint i+1 expressed in base)
        o_i = T_i[:3, 3]
        a, alpha, d, theta, jtype = dh[i]
        if jtype == 'R':
            Jv = np.cross(z, o_n - o_i)
            Jw = z
        else:  # prismatic
            Jv = z
            Jw = np.zeros(3)
        J[:3, i] = Jv
        J[3:, i] = Jw
    return J

# orientation error as rotation vector (3)
def orientation_error(R_target, R_current):
    R_err = R_target @ R_current.T
    rotvec = R.from_matrix(R_err).as_rotvec()
    return rotvec

# Damped Least Squares IK step
def ik_damped_ls(dh, target_pos, target_rot_mat,
                 joint_types,
                 q_limits=None,
                 max_iters=200,
                 tol_pos=1e-4,
                 tol_ori=1e-3,
                 lambda0=0.01,
                 step_scale=1.0,
                 q_nominal=None,
                 secondary_gain=0.1):
    """
    dh: list (a,alpha,d,theta,jtype) with current theta/d values as initial guess
    joint_types: list of 'R' or 'P' (same order)
    q_limits: (lower, upper) arrays or None
    q_nominal: preferowana pozycja w przestrzeni null-space (np array) or None
    """
    n = len(dh)
    # extract q (variables) from dh
    def get_q(dh):
        return np.array([x[3] if x[4]=='P' else x[3] for x in dh], dtype=float)
    def set_q(dh, q):
        new = []
        for i, (a,alpha,d,theta,jt) in enumerate(dh):
            if jt == 'R':
                new.append((a,alpha,d,q[i],jt))
            else:
                new.append((a,alpha,q[i],theta,jt))
        return new

    q = get_q(dh)
    for it in range(max_iters):
        dh_current = set_q(dh, q)
        T, _ = forward_kinematics(dh_current)
        pos = T[:3,3]
        Rcur = T[:3,:3]

        e_pos = (target_pos - pos)
        e_ori = orientation_error(target_rot_mat, Rcur)  # 3-vector
        err = np.concatenate([e_pos, e_ori])

        if np.linalg.norm(e_pos) < tol_pos and np.linalg.norm(e_ori) < tol_ori:
            return q, True, it

        J = compute_jacobian(dh_current)  # 6 x n

        # Damped least squares solution: qdot = J^T (J J^T + lambda^2 I)^-1 * err
        lambda2 = lambda0**2
        JJt = J @ J.T
        inv_term = inv(JJt + lambda2 * np.eye(6))
        qdot = J.T @ (inv_term @ err)

        # optional secondary objective: stay near q_nominal using null-space projection
        if q_nominal is not None:
            J_pinv = J.T @ inv(J @ J.T + lambda2 * np.eye(6))
            null_proj = np.eye(n) - J_pinv @ J
            qdot0 = -secondary_gain * (q - q_nominal)
            qdot = qdot + null_proj @ qdot0

        # apply step, clip by joint limits
        q = q + step_scale * qdot
        if q_limits is not None:
            q = np.minimum(np.maximum(q, q_limits[0]), q_limits[1])

    return q, False, max_iters




# ----------------------------
# PRZYKŁAD użycia (schemat):
# dh = [
#   (a1, alpha1, d1, theta1, 'R'),
#   (a2, alpha2, d2, theta2, 'R'),
#   ...
# ]
# target_pos = np.array([x,y,z])
# target_rot_mat = np.eye(3)  # docelowa orientacja (3x3)
# q_limits = (np.array(lower_bounds), np.array(upper_bounds))
# q_nominal = np.zeros(n)
# q_sol, ok, iters = ik_damped_ls(dh, target_pos, target_rot_mat, joint_types, q_limits, q_nominal=q_nominal)


rad_30 = np.radians(30.0)
rad_180 = np.radians(180.0)

dh = [
  (20.0, 0, 0, rad_30, 'R'),
  (20.0, 0, 0, rad_30, 'R'),
  (20.0, 0, 0, rad_30, 'R'),
]

target_pos = np.array([40.0,40.0,0.0])
target_rot_mat = np.eye(3)  # docelowa orientacja (3x3)
q_limits = (np.array([-rad_180,-rad_180,-rad_180]), np.array([rad_180,rad_180,rad_180]))
q_nominal = np.zeros(3)
q_sol, ok, iters = ik_damped_ls(dh, target_pos, target_rot_mat, ['R','R','R'], q_limits, q_nominal=q_nominal)

print("Solution:", np.degrees(q_sol))
print("Success:", ok, "Iterations:", iters)
