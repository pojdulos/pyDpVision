from dpVision import AP, DHJoint

def build_scene_from_dh_dictionary(hand_model):
	joints = {}
	for joint_name, params in hand_model.items():
		joint = DHJoint(
			theta = params['theta_deg'],
			d = params['d'],
			a = params['a'],
			alpha = params['alpha_deg'],
			theta_variable = params['theta_variable'],
			d_variable = params['d_variable'],
			name = joint_name
		)
        
		joint.theta_limits = params.get('theta_limits', [-180.0, 180.0])
		joint.d_limits = params.get('d_limits', [-100.0, 100.0])
		joint.a_limits = params.get('a_limits', [-100.0, 100.0])
		joint.alpha_limits = params.get('alpha_limits', [-180.0, 180.0])
           
		parent_name = params['parent_joint']
		if parent_name is not None and parent_name in joints:
			parent_joint = joints[parent_name]
			AP.addObject(joint, parent_joint)
		else:
			AP.addObject(joint)
		joints[joint_name] = joint

	#test_point = AnnotationSphere()
	#test_point.radius = 3.0
	#test_point.setColor(255,0,0,255)
	
	#AP.addObject(test_point, joints['joint2'])

	AP.updateAllViews()

	# curling five fingers (proximal, middle, distal)
	# curl_pose = {
	# 'index_proximal': 60.0, 'index_middle': 45.0, 'index_distal': 30.0,
	# 'middle_proximal': 65.0,'middle_middle': 50.0,'middle_distal': 35.0,
	# 'ring_proximal': 60.0, 'ring_middle': 45.0, 'ring_distal': 30.0,
	# 'pinky_proximal': 55.0, 'pinky_middle': 40.0, 'pinky_distal': 30.0,
	# 'thumb_proximal': 40.0,'thumb_distal': 20.0
	# }
	# for name, ang in curl_pose.items():
	# 	joints[name].set_theta_deg(ang)
	# 	AP.updateAllViews()
	return joints

# prosty animator QTimer dla joints (DHJoint)
# joints: dict name->DHJoint (obiekt musi mieć metody set_theta_deg/get_theta_deg oraz set_d/get_d)
# poses: lista słowników { joint_name: value, ... } -- wartości w stopniach dla theta, w jednostkach dla d
# duration_ms: czas przejścia między kolejnymi pose'ami (ms)
# fps: jak często odświeżać (klatki/s)

from PyQt5.QtCore import QTimer
import time

def prepare_animation(joints, poses, duration_ms=800, fps=30, loop=True):
    if not poses or len(poses) < 2:
        raise ValueError("Podaj co najmniej 2 pozy do animacji (poses).")

    # sprawdź, czy QApplication istnieje
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance() is None:
        raise RuntimeError("Nie ma działającego QApplication. Uruchom najpierw GUI.")

    # upewnij się, że poses zawierają tylko istniejące jointy (albo ignoruj brakujące)
    all_joint_names = set(joints.keys())
    for p in poses:
        for name in list(p.keys()):
            if name not in all_joint_names:
                raise KeyError(f"Pose zawiera nieznany joint: {name}")

    # wewnętrzny stan animacji
    state = {
        'cur_idx': 0,
        'next_idx': 1,
        't0': time.time(),
        'duration': duration_ms / 1000.0,
        'running': True
    }

    # pomoc: pobierz startowe wartości dla przejścia (na początku lub po przeskoku)
    def capture_start_values():
        start_pose = poses[state['cur_idx']]
        end_pose = poses[state['next_idx']]
        starts = {}
        ends = {}
        for name in set(list(start_pose.keys()) + list(end_pose.keys())):
            joint = joints[name]
            # jeśli joint sterujemy kątem (theta_variable=True) to zakładamy wartości w stopniach
            if getattr(joint, 'theta_variable', False) and not getattr(joint, 'd_variable', False):
                starts[name] = joint.get_theta_deg()
                ends[name] = end_pose.get(name, starts[name])
            elif getattr(joint, 'd_variable', False) and not getattr(joint, 'theta_variable', False):
                starts[name] = joint.d if hasattr(joint, 'd') else joint.getTranslation()[2]  # fallback
                ends[name] = end_pose.get(name, starts[name])
            else:
                # jeśli oba true lub oba false - przyjmij, że w pose podana jest theta (stopnie) jeśli występuje,
                # w przeciwnym razie d; fallback na theta
                if name in end_pose:
                    if isinstance(end_pose[name], (int, float)):
                        starts[name] = joint.get_theta_deg() if hasattr(joint, 'get_theta_deg') else 0.0
                        ends[name] = end_pose[name]
                    else:
                        starts[name] = joint.d if hasattr(joint, 'd') else 0.0
                        ends[name] = end_pose[name]
                else:
                    starts[name] = joint.get_theta_deg() if hasattr(joint, 'get_theta_deg') else 0.0
                    ends[name] = starts[name]
        return starts, ends

    starts, ends = capture_start_values()

    interval_ms = int(1000.0 / float(fps))
    timer = QTimer()
    timer.setInterval(interval_ms)

    def on_tick():
        now = time.time()
        t = (now - state['t0']) / state['duration']
        if t >= 1.0:
            # zakończenie kroku — ustaw dokładnie wartości końcowe
            for name, endv in ends.items():
                joint = joints[name]
                if getattr(joint, 'theta_variable', False) and not getattr(joint, 'd_variable', False):
                    joint.set_theta_deg(endv)
                elif getattr(joint, 'd_variable', False) and not getattr(joint, 'theta_variable', False):
                    joint.set_d(endv)
                else:
                    # prefer theta if present in end pose
                    if name in poses[state['next_idx']]:
                        joint.set_theta_deg(poses[state['next_idx']][name])
                    else:
                        joint.set_d(poses[state['next_idx']].get(name, getattr(joint, 'd', 0.0)))
            # odśwież
            try:
                AP.updateAllViews()
            except Exception:
                pass

            # przejdź do następnej pary
            state['cur_idx'] = state['next_idx']
            state['next_idx'] = (state['next_idx'] + 1) % len(poses) if loop else state['next_idx'] + 1
            if state['next_idx'] >= len(poses):
                # koniec animacji
                timer.stop()
                state['running'] = False
                return
            state['t0'] = time.time()
            # przygotuj nowe starts/ends
            nonlocal_starts_ends = capture_start_values()
            # assign back
            nonlocal_starts_ends_local = nonlocal_starts_ends
            # workaround to update outer starts/ends
            starts.clear(); starts.update(nonlocal_starts_ends_local[0])
            ends.clear(); ends.update(nonlocal_starts_ends_local[1])
            return

        # interpoluj
        for name in starts.keys():
            s = starts[name]; e = ends[name]
            v = s + (e - s) * t
            joint = joints[name]
            if getattr(joint, 'theta_variable', False) and not getattr(joint, 'd_variable', False):
                joint.set_theta_deg(v)
            elif getattr(joint, 'd_variable', False) and not getattr(joint, 'theta_variable', False):
                joint.set_d(v)
            else:
                # prefer setting theta if the end pose specified theta (common case)
                if name in poses[state['next_idx']]:
                    joint.set_theta_deg(v)
                else:
                    joint.set_d(v)

        # odśwież widoki
        try:
            AP.updateAllViews()
            AP.updateProperties()
        except Exception:
            pass

    # start
    state['t0'] = time.time()
    timer.timeout.connect(on_tick)
    return timer  # zwróć timer, żeby caller mógł go zatrzymać: timer.stop()



# poses: lista keyframe'ów; wartości kątów w stopniach (theta). 
# Dla każdego palca ustawiamy prox/middle/distal (jeśli istnieją).

poses = []

# 0. POZYCJA WYJŚCIOWA — dłoń otwarta (neutral)
poses.append({
    'index_proximal': 0.0, 'index_middle': 0.0, 'index_distal': 0.0,
    'middle_proximal': 0.0, 'middle_middle': 0.0, 'middle_distal': 0.0,
    'ring_proximal': 0.0, 'ring_middle': 0.0, 'ring_distal': 0.0,
    'pinky_proximal': 0.0, 'pinky_middle': 0.0, 'pinky_distal': 0.0,
    'thumb_proximal': 0.0, 'thumb_distal': 0.0, 'thumb_base': 50.0
})

# # Helper: pojedyncze zwinięcie palca (proximal -> middle -> distal)
# def add_curl_seq(prox, mid, dist, prox_angle=60, mid_angle=45, dist_angle=30):
#     # stopniowe zwijanie: najpierw proximal, potem middle, potem distal
#     poses.append({prox: prox_angle})                 # zgięcie proximal
#     poses.append({mid: mid_angle})                   # zgięcie middle
#     poses.append({dist: dist_angle})                 # zgięcie distal
#     # dla płynności dodaj pose z całościowym zgięciem palca
#     poses.append({prox: prox_angle, mid: mid_angle, dist: dist_angle})

# # Index
# add_curl_seq('index_proximal', 'index_middle', 'index_distal', prox_angle=70, mid_angle=50, dist_angle=35)
# # rozwiń index (wróć do neutral) — pojedynczy keyframe ustawiający 0
# poses.append({'index_proximal': 0.0, 'index_middle': 0.0, 'index_distal': 0.0})

# # Middle
# add_curl_seq('middle_proximal', 'middle_middle', 'middle_distal', prox_angle=75, mid_angle=55, dist_angle=40)
# poses.append({'middle_proximal': 0.0, 'middle_middle': 0.0, 'middle_distal': 0.0})

# # Ring
# add_curl_seq('ring_proximal', 'ring_middle', 'ring_distal', prox_angle=70, mid_angle=50, dist_angle=35)
# poses.append({'ring_proximal': 0.0, 'ring_middle': 0.0, 'ring_distal': 0.0})

# # Pinky
# add_curl_seq('pinky_proximal', 'pinky_middle', 'pinky_distal', prox_angle=65, mid_angle=45, dist_angle=35)
# poses.append({'pinky_proximal': 0.0, 'pinky_middle': 0.0, 'pinky_distal': 0.0})

# # Thumb (zwijanie z udziałem base + prox + distal)
# # Najpierw odwiedzenie (przybliżenie kciuka) -> potem zginanie paliczków
# poses.append({'thumb_base': 25.0})   # abdukcja/przybliżenie kciuka
# poses.append({'thumb_proximal': 40.0})
# poses.append({'thumb_distal': 25.0})
# poses.append({'thumb_base': 25.0, 'thumb_proximal': 40.0, 'thumb_distal': 25.0})
# # rozwiń kciuk
# poses.append({'thumb_base': 0.0, 'thumb_proximal': 0.0, 'thumb_distal': 0.0})

# # Teraz sekwencja: kolejno zwijanie wszystkich palców (prox->mid->dist dla każdego), dając efekt mocnego chwytu
# # 1) proximal-y wszystkich palców
# poses.append({
#     'index_proximal': 80.0,
#     'middle_proximal': 85.0,
#     'ring_proximal': 80.0,
#     'pinky_proximal': 70.0,
#     'thumb_proximal': 50.0
# })
# # 2) middle-y
# poses.append({
#     'index_middle': 60.0,
#     'middle_middle': 65.0,
#     'ring_middle': 60.0,
#     'pinky_middle': 50.0
# })
# # 3) distal-y
# poses.append({
#     'index_distal': 40.0,
#     'middle_distal': 45.0,
#     'ring_distal': 40.0,
#     'pinky_distal': 35.0,
#     'thumb_distal': 30.0
# })
# # 4) zamknięcie kciuka do chwytu pincher / power
# poses.append({'thumb_base': 35.0, 'thumb_proximal': 55.0, 'thumb_distal': 30.0})

# Pełne zaciśnięcie (all together)
poses.append({
    'index_proximal': 80.0, 'index_middle': 60.0, 'index_distal': 40.0,
    'middle_proximal': 85.0, 'middle_middle': 65.0, 'middle_distal': 45.0,
    'ring_proximal': 80.0, 'ring_middle': 60.0, 'ring_distal': 40.0,
    'pinky_proximal': 70.0, 'pinky_middle': 50.0, 'pinky_distal': 35.0,
    'thumb_base': 85.0, 'thumb_proximal': 55.0, 'thumb_distal': 30.0
})

# Rozluźnienie — stopniowe rozprostowanie (możesz dodać intermediate frames jeśli chcesz płynniejsze)
poses.append({
    'index_proximal': 30.0, 'index_middle': 20.0, 'index_distal': 10.0,
    'middle_proximal': 35.0, 'middle_middle': 25.0, 'middle_distal': 15.0,
    'ring_proximal': 30.0, 'ring_middle': 20.0, 'ring_distal': 10.0,
    'pinky_proximal': 25.0, 'pinky_middle': 18.0, 'pinky_distal': 12.0,
    'thumb_base': 65.0, 'thumb_proximal': 20.0, 'thumb_distal': 10.0
})

# Powrót do neutral
poses.append({
    'index_proximal': 0.0, 'index_middle': 0.0, 'index_distal': 0.0,
    'middle_proximal': 0.0, 'middle_middle': 0.0, 'middle_distal': 0.0,
    'ring_proximal': 0.0, 'ring_middle': 0.0, 'ring_distal': 0.0,
    'pinky_proximal': 0.0, 'pinky_middle': 0.0, 'pinky_distal': 0.0,
    'thumb_base': 50.0, 'thumb_proximal': 0.0, 'thumb_distal': 0.0
})


# from hand_model import hand_model

# def create_hand_animation_demo():
# 	joints = build_scene_from_dh_dictionary(hand_model)
# 	timer = prepare_animation(joints, poses, duration_ms=700, fps=30, loop=True)
# 	return timer