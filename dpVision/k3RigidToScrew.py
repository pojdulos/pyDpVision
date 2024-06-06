import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.tri as mtri

def K3BigL():
    X = np.array([[0., 1.],
                  [0., 1.],
                  [0., 2.],
                  [0., 2.]])

    Y = np.array([[4., 4.],
                  [2., 2.],
                  [1., 1.],
                  [0., 0.]])

    Z = np.zeros_like(X)

    return X, Y, Z

# def K3MoveMesh(M, XL, YL, ZL):
#     rows, cols = XL.shape
#     XLP = np.zeros_like(XL, dtype=float)
#     YLP = np.zeros_like(YL, dtype=float)
#     ZLP = np.zeros_like(ZL, dtype=float)

#     for j in range(rows):
#         for i in range(cols):
#             X = np.array([XL[j, i], YL[j, i], ZL[j, i], 1.0])
#             XP = np.dot(M, X)
#             XP /= XP[3]
#             XLP[j, i] = XP[0]
#             YLP[j, i] = XP[1]
#             ZLP[j, i] = XP[2]

#     return XLP, YLP, ZLP

def K3MoveMesh(M, XL, YL, ZL):
    # Rozmiar macierzy
    rows, cols = XL.shape

    # Przygotuj macierze wynikowe
    X = np.vstack([XL.flatten(), YL.flatten(), ZL.flatten(), np.ones(rows * cols)])
    XP = np.dot(M, X)

    # Podziel przez czwartą współrzędną
    XP /= XP[3, :]

    # Przekształć z powrotem do pierwotnego kształtu
    XLP, YLP, ZLP = XP[:3, :].reshape(3, rows, cols)

    return XLP, YLP, ZLP


def K3Fletch(V):
    # Find smallest component of V:
    imin = np.argmin(np.abs(V))
    
    XV = np.zeros(3)
    XV[imin] = 1.0  # Guaranteed not parallel to V
    
    YV = np.cross(XV, V)  # Guaranteed perpendicular to V
    YV = K3Normalize(YV)
    
    XV = np.cross(YV, V)  # Guaranteed perpendicular to V and YV
    XV = -K3Normalize(XV)
    
    return XV, YV

def K3Normalize(V):
    #tu należało by sprawdzać czy długość != 0, ale w tym przypadku to pomijam
    return V / np.linalg.norm(V)

def K3AxisVersor(R):
    A = R - np.eye(3)
    u, s, V = np.linalg.svd(A) # Obliczanie wektorów własnych

    print('U1=',u)
    print('s1=',s)
    print("V1 = ", V)

    V7 = V[-1]  # Ostatni wektor własny odpowiadający zerowej wartości własnej
    V = V7 / np.linalg.norm(V7) if not np.allclose(V7, 0) else np.array([0, 0, 0])
    return V

def null_space(A, rcond=None):
    print('A=',A)
    u, s, vh = np.linalg.svd(A, full_matrices=True)
    print('U2=',u)
    print('s2=',s)
    print('V2=',vh)
    rcond = np.finfo(s.dtype).eps if rcond is None else rcond
    null_mask = (s <= rcond * s[0])
    null_space = np.compress(null_mask, vh, axis=0)
    result = np.conjugate(null_space).T
    print('null_space result=',result)
    return result

def K3RigidToScrew(M):
    R = M[:3, :3]
    T = M[:3, 3]

    #print('R=',R)
    V = K3AxisVersor(R)
    print('axis versor = ', V)

    if np.linalg.norm(V) == 0:
        # Crash if no rotation detected, i.e. pure translation
        # (temporary solution before we decide what to do)
        print('no rotation detected')
        return [1., 0., 0.], 0.0, [0., 0., 0.], [0., 0., 0.]
    else:
        # Now determine the angle.
        # First, construct two versors
        # perpendicular to V and to each other:
        XV, YV = K3Fletch(V)
        XVP = np.dot(R, XV)
        
        # Now rotate one of them by R and get alpha:
        alpha = np.arctan2(np.dot(XVP, YV), np.dot(XVP, XV))
        #print('alpha = ', np.degrees(alpha))
        
        # find axial shift t:
        dist = np.dot(V.T, T).T     # dist = (V' * T)' tu moznaby pominąć te transpozycje,
                                    # bo python sobie sam potrafi transponować wektor
                                    # jeśli jest taka potrzeba dla poprawności mnożenia
        print('dist=',dist)
        t = V * dist   
        #print('t = ',t)

        # Now find position of axis (its direction is known)
        D = T - t
        MP = M - np.column_stack([np.zeros((4, 3)), np.append(t, 0)]) - np.eye(4)
        #print('MP = ', MP)

        #D7 = np.linalg.matrix_rank(MP) # to zwraca liczbę równą rzędowi macierzy
        
        D7 = null_space(MP)             # a to konkretne wektory
        print('D7 = ', D7)
        print(D7.shape)
        if D7.ndim == 1:
            D = D7[:3] * (1 / D7[3])
            #print('MONO')
        else:
            #print('STEREO')
            D = np.zeros(4)

            # get sum of non-infinite points:
            for i in range(D7.shape[1]):
                print('i = ', i)
                if abs(D7[3, i]) > 0.0001:
                    print('D7 = ', D7)
                    D7a = D7[:, i] * (1 / D7[3, i])
                    print('D7a = ', D7a)
                    D += D7a
                    print('i = ', i, 'D = ', D)

            D = D[:3] * (1 / D[3])
            print('Normalized D = ',D)
            return V, alpha, D, t

def K3Projection(P, Q, v):
    u = [P[0] - Q[0], P[1] - Q[1], P[2] - Q[2]]
    dot_product = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    v_length_squared = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
    scalar = dot_product / v_length_squared
    projection_point = [Q[0] + scalar * v[0], Q[1] + scalar * v[1], Q[2] + scalar * v[2]]
    return projection_point

def test1():
    #M = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
    theta = np.pi / 6
    M = np.array([
        [np.cos(theta), 0, np.sin(theta), 5],
        [0, 1, 0, 0],
        [-np.sin(theta), 0, np.cos(theta), 0],
        [0,0,0,1]
    ])

    V, alpha, D, t = K3RigidToScrew(M)
    print('V =',V, 'alpha =',np.degrees(alpha), 'D =',D, 't =',t)

def K3Rot3D():
    # Generuj transformację
    alfa = np.pi / 3 #-0.2
    betta = np.pi / 4 #0.0
    gama = 0.0

    Rx = np.array([[1, 0, 0], [0, np.cos(alfa), -np.sin(alfa)], [0, np.sin(alfa), np.cos(alfa)]])
    Ry = np.array([[np.cos(betta), 0, np.sin(betta)], [0, 1, 0], [-np.sin(betta), 0, np.cos(betta)]])
    Rz = np.array([[np.cos(gama), -np.sin(gama), 0], [np.sin(gama), np.cos(gama), 0], [0, 0, 1]])
    R = np.dot(Rz, np.dot(Ry, Rx))

    T = np.array([0.7, 2.0, 0.3])
    #T = np.array([2, 0, 1])
    M = np.vstack([np.hstack([R, T.reshape(-1, 1)]), [0, 0, 0, 1]])
    #print('M =',M)

    # Wywołaj procedurę
    V, alpha, D, t = K3RigidToScrew(M)
    print('V =',V, 'alpha =',np.degrees(alpha), 'D =',D, 't =',t)

    # Przygotuj okienko
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Pokaż siatkę przed transformacją
    XL, YL, ZL = K3BigL()
    ax.plot_surface(XL, YL, ZL, color='g', shade=False)

    # Pokaż siatkę po transformacji
    XLP, YLP, ZLP = K3MoveMesh(M, XL, YL, ZL)
    ax.plot_surface(XLP, YLP, ZLP, color='b', shade=False)

    #pokaż punkt D
    ax.scatter(D[0], D[1], D[2], color='y', marker='x')
    
    # Pokaż oś
    A = np.vstack([ D - 3 * V, D + 3 * V ])
    ax.plot(A[:,0], A[:,1], A[:,2], color='r')
    ax.scatter(A[1,0], A[1,1], A[1,2], color='r', marker='o') # zamiast strzałki

    plt.show()

#test1()
#K3Rot3D()

# A = [[1.,2.,3.],[1.,2.,3.],[1.,2.,3.]]
# n = null_space(A)

# print (n)

