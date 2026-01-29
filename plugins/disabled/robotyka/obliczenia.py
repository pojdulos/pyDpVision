import numpy as np
from scipy.linalg import pinv, inv
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares

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
        z = T_i[:3, 2]   # axis of rotation for joint i (expressed in base frame)
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

# --- UŻYTECZNE FUNKCJE WYKORZYSTUJĄCE JACOBIAN ---

def compute_manipulability(dh, planar=False):
    """
    Yoshikawa manipulability measure - wskaźnik "sprawności" robota w danej konfiguracji.
    Wysoka wartość = robot daleko od singularities, może poruszać się łatwo we wszystkich kierunkach.
    Niska wartość = blisko singularity, trudności z ruchem w niektórych kierunkach.
    
    Args:
        dh: DH table
        planar: if True, compute 2D manipulability for planar robots (only x,y)
    """
    J = compute_jacobian(dh)
    Jv = J[:3, :]  # część liniowa (pozycja)
    
    if planar:
        # Dla robotów planarnych (XY) - używamy tylko 2 wierszy
        Jv_2d = Jv[:2, :]  # tylko x, y
        w = np.sqrt(np.abs(np.linalg.det(Jv_2d @ Jv_2d.T)))
    else:
        # Dla robotów 3D
        w = np.sqrt(np.abs(np.linalg.det(Jv @ Jv.T)))
    
    return w

def check_singularity(dh, threshold=1e-3, planar=False):
    """
    Sprawdza czy robot jest blisko singularity (osobliwości).
    Returns: (is_singular, manipulability, condition_number)
    """
    J = compute_jacobian(dh)
    Jv = J[:3, :]
    
    if planar:
        Jv = Jv[:2, :]  # tylko x, y dla robotów planarnych
    
    manip = compute_manipulability(dh, planar=planar)
    
    # Condition number - im większy, tym gorzej
    try:
        cond = np.linalg.cond(Jv)
    except:
        cond = np.inf
    
    is_singular = manip < threshold or cond > 1000
    return is_singular, manip, cond

def compute_joint_velocities(dh, end_effector_velocity):
    """
    Odwrotna kinematyka prędkości: prędkość end-effectora -> prędkości przegubów.
    end_effector_velocity: [vx, vy, vz, wx, wy, wz] (liniowa + kątowa) lub [vx, vy, vz]
    Returns: qdot (prędkości przegubów)
    """
    J = compute_jacobian(dh)
    
    if len(end_effector_velocity) == 3:
        # tylko prędkość liniowa
        Jv = J[:3, :]
        qdot = pinv(Jv) @ end_effector_velocity
    else:
        # pełna prędkość (6 DOF)
        qdot = pinv(J) @ end_effector_velocity
    
    return qdot

def compute_reachable_velocities(dh, q_dot_max):
    """
    Dla danych maksymalnych prędkości przegubów, oblicza maksymalną prędkość end-effectora.
    q_dot_max: array of max joint velocities
    Returns: max linear velocity magnitude
    """
    J = compute_jacobian(dh)
    Jv = J[:3, :]
    
    # Elipsoida prędkości - maksymalna prędkość w każdym kierunku
    # Maksymalna prędkość to największa wartość własna
    M = Jv @ np.diag(q_dot_max**2) @ Jv.T
    eigenvalues = np.linalg.eigvalsh(M)
    max_vel = np.sqrt(np.max(eigenvalues))
    
    return max_vel

def compute_force_analysis(dh, end_effector_force):
    """
    Statyczna analiza sił: siła na end-effectorze -> momenty w przegubach.
    end_effector_force: [fx, fy, fz] lub [fx, fy, fz, mx, my, mz]
    Returns: tau (momenty/siły w przegubach)
    """
    J = compute_jacobian(dh)
    
    if len(end_effector_force) == 3:
        Jv = J[:3, :]
        tau = Jv.T @ end_effector_force
    else:
        tau = J.T @ end_effector_force
    
    return tau

def find_null_space_motion(dh):
    """
    Znajduje ruch w null-space Jakobianu - ruch przegubów, który NIE zmienia pozycji end-effectora.
    Przydatne dla robotów redundantnych (więcej przegubów niż DOF zadania).
    Returns: null_space_basis (kolumny to wektory bazowe null-space)
    """
    J = compute_jacobian(dh)
    Jv = J[:3, :]
    
    # SVD decomposition
    U, S, Vt = np.linalg.svd(Jv)
    
    # Null space to wektory odpowiadające wartościom własnym = 0
    rank = np.sum(S > 1e-10)
    null_space = Vt[rank:, :].T
    
    return null_space

def optimize_configuration_for_manipulability(dh_template, target_pos, q_limits, planar=True):
    """
    Znajduje konfigurację IK, która maksymalizuje manipulability (unika singularities).
    
    Args:
        dh_template: DH table
        target_pos: target position
        q_limits: (q_min, q_max)
        planar: if True, use 2D manipulability for planar robots
    """
    def objective(q):
        dh_current = set_q(dh_template, q)
        T, _ = forward_kinematics(dh_current)
        pos = T[:3, 3]
        
        # Błąd pozycji (główny cel)
        pos_error = np.linalg.norm(pos - target_pos)
        
        # Kara za niską manipulability (cel wtórny)
        manip = compute_manipulability(dh_current, planar=planar)
        manip_penalty = 1.0 / (manip + 0.01)  # im niższa manip, tym wyższa kara
        
        return pos_error * 100 + manip_penalty
    
    from scipy.optimize import minimize
    q0 = np.array([item[3] for item in dh_template])
    
    result = minimize(objective, q0, bounds=list(zip(q_limits[0], q_limits[1])), method='SLSQP')
    return result.x, result.success

def set_q(dh_template, q):
    out = []
    for i,(a,alpha,d,theta,jt) in enumerate(dh_template):
        if jt=='R':
            out.append((a,alpha,d,q[i],jt))
        else:
            out.append((a,alpha,q[i],theta,jt))
    return out



dh_deg = [
  (20.0, 0.0, 0.0, 30.0, 'R'),
  (20.0, 0.0, 0.0, 30.0, 'R'),
  (20.0, 0.0, 0.0, 30.0, 'R'),
]

# Funkcja IK z opcjonalną kontrolą orientacji
def solve_ik(dh, target_pos, target_rot_mat=None, q_limits=None, q0=None, 
             weights_pos=None, weights_ori=None, xtol=1e-9, ftol=1e-9):
    """
    Inverse kinematics using scipy.optimize.least_squares
    
    Args:
        dh: DH table [(a, alpha, d, theta, jtype), ...]
        target_pos: target position [x, y, z]
        target_rot_mat: target rotation matrix (3x3) or None (position-only IK)
        q_limits: (q_min, q_max) arrays or None
        q0: initial guess or None (uses current values from dh)
        weights_pos: weight vector for position errors [wx, wy, wz] or None
        weights_ori: weight for orientation error (scalar) or None
        xtol, ftol: tolerances for least_squares
    
    Returns:
        q_solution: joint angles/positions
        success: bool
        result: full least_squares result object
    """
    def set_q_local(dh, q):
        return [(a,alpha,d,q[i],jt) for i,(a,alpha,d,_,jt) in enumerate(dh)]
    
    if q0 is None:
        q0 = np.array([item[3] for item in dh])
    
    # Position-only IK
    if target_rot_mat is None:
        def residuals(q):
            T, _ = forward_kinematics(set_q_local(dh, q))
            pos = T[:3,3]
            err = pos - target_pos
            if weights_pos is not None:
                err = err * weights_pos
            return err
    
    # Position + Orientation IK
    else:
        def residuals(q):
            T, _ = forward_kinematics(set_q_local(dh, q))
            pos = T[:3,3]
            Rcur = T[:3,:3]
            
            e_pos = pos - target_pos
            if weights_pos is not None:
                e_pos = e_pos * weights_pos
            
            e_ori = orientation_error(target_rot_mat, Rcur)
            if weights_ori is not None:
                e_ori = e_ori * weights_ori
            
            return np.concatenate([e_pos, e_ori])
    
    # Solve
    if q_limits is not None:
        res = least_squares(residuals, q0, bounds=q_limits, xtol=xtol, ftol=ftol)
    else:
        res = least_squares(residuals, q0, xtol=xtol, ftol=ftol)
    
    return res.x, res.success, res


# konwersja do radianów
dh_rad = [(a,alpha,d, np.deg2rad(theta) if jt=='R' else theta, jt) for (a,alpha,d,theta,jt) in dh_deg]

target_pos = np.array([20.0,40.0,0.0])
target_rot = None  # None = position-only IK, np.eye(3) = with orientation
q_min = np.deg2rad(np.array([-180.0,-180.0,-180.0]))
q_max = np.deg2rad(np.array([180.0,180.0,180.0]))

print("=" * 70)
print("EXAMPLE 1: Position-only IK")
print("=" * 70)
q_sol, success, res = solve_ik(dh_rad, target_pos, target_rot_mat=None, 
                                 q_limits=(q_min, q_max))
q_sol_deg = np.rad2deg(q_sol)
Tfinal, _ = forward_kinematics(set_q(dh_rad, q_sol))
final_pos = Tfinal[:3,3]
err_pos = np.linalg.norm(final_pos - target_pos)

print(f"Success: {success}")
print(f"Function evals: {res.nfev}")
print(f"q [deg]: {q_sol_deg}")
print(f"Final pos: {final_pos}")
print(f"Position error: {err_pos:.9f}")
print()

print("=" * 70)
print("EXAMPLE 2: Position + Orientation IK")
print("=" * 70)
target_rot_mat = np.eye(3)  # Identity = żadnej rotacji
q_sol2, success2, res2 = solve_ik(dh_rad, target_pos, target_rot_mat=target_rot_mat, 
                                    q_limits=(q_min, q_max))
q_sol2_deg = np.rad2deg(q_sol2)
Tfinal2, _ = forward_kinematics(set_q(dh_rad, q_sol2))
final_pos2 = Tfinal2[:3,3]
final_rot2 = Tfinal2[:3,:3]
err_pos2 = np.linalg.norm(final_pos2 - target_pos)
err_ori2 = np.linalg.norm(orientation_error(target_rot_mat, final_rot2))

print(f"Success: {success2}")
print(f"Function evals: {res2.nfev}")
print(f"q [deg]: {q_sol2_deg}")
print(f"Final pos: {final_pos2}")
print(f"Position error: {err_pos2:.9f}")
print(f"Orientation error: {err_ori2:.9f}")
print()

# --- DODATKOWE ANALIZY Z JAKOBIANEM ---
print("=" * 70)
print("EXAMPLE 3: Analiza Jakobianu (dla robota planarnego)")
print("=" * 70)

# Sprawdzenie singularity - używamy planar=True dla robotów 3R pracujących w XY
is_sing, manip, cond = check_singularity(set_q(dh_rad, q_sol), planar=True)
print(f"Configuration 1 (q = {q_sol_deg}):")
print(f"  Manipulability (2D): {manip:.6f}")
print(f"  Condition number: {cond:.2f}")
print(f"  Near singularity: {is_sing}")
print()

# Analiza prędkości
print("Velocity Analysis:")
ee_vel = np.array([1.0, 0.0, 0.0])  # 1 m/s w kierunku X
joint_vel = compute_joint_velocities(set_q(dh_rad, q_sol), ee_vel)
print(f"  End-effector velocity: {ee_vel} m/s")
print(f"  Required joint velocities: {np.rad2deg(joint_vel)} deg/s")
print()

# Maksymalna prędkość
q_dot_max = np.ones(3) * np.deg2rad(60)  # max 60 deg/s na przegub
max_vel = compute_reachable_velocities(set_q(dh_rad, q_sol), q_dot_max)
print(f"  Max joint velocities: 60 deg/s each")
print(f"  Max end-effector velocity: {max_vel:.3f} m/s")
print()

# Analiza sił
print("Force Analysis:")
ee_force = np.array([0.0, 0.0, -10.0])  # 10N w dół (ciężar)
joint_torques = compute_force_analysis(set_q(dh_rad, q_sol), ee_force)
print(f"  End-effector force: {ee_force} N")
print(f"  Required joint torques: {joint_torques} Nm")
print()

# Null space (dla robotów redundantnych)
null_space = find_null_space_motion(set_q(dh_rad, q_sol))
if null_space.shape[1] > 0:
    print(f"Null-space dimension: {null_space.shape[1]}")
    print(f"Null-space basis:\n{null_space}")
else:
    print("No null-space (robot is not redundant for this task)")
print()

# Optymalizacja pod kątem manipulability
print("=" * 70)
print("EXAMPLE 4: IK z optymalizacją manipulability (2D)")
print("=" * 70)
q_opt, success_opt = optimize_configuration_for_manipulability(dh_rad, target_pos, (q_min, q_max))
q_opt_deg = np.rad2deg(q_opt)
manip_opt = compute_manipulability(set_q(dh_rad, q_opt), planar=True)
T_opt, _ = forward_kinematics(set_q(dh_rad, q_opt))
pos_opt = T_opt[:3, 3]

print(f"Success: {success_opt}")
print(f"q [deg]: {q_opt_deg}")
print(f"Position: {pos_opt}")
print(f"Manipulability (2D): {manip_opt:.6f}")
print(f"Compare to standard IK manipulability: {manip:.6f}")

# Bezpieczne obliczenie improvement
if manip > 1e-10 and manip_opt > 1e-10:
    improvement = (manip_opt/manip - 1)*100
    print(f"Improvement: {improvement:.1f}%")
elif manip_opt > manip:
    print(f"Improvement: Better (both near zero, but opt={manip_opt:.9f} > std={manip:.9f})")
else:
    print(f"Improvement: N/A (robot is planar - manipulability is naturally 0)")
print()
print("Note: For planar robots (3R working in 2D), manipulability is often 0.")
print("      Use condition number or other metrics for better analysis.")