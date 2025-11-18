simple_model = {
    'joint1' : {
        'theta_deg' : 45.0,
        'd' : 10.0,
        'a' : 5.0,
        'alpha_deg' : 30.0,
        'theta_variable' : True,
        'd_variable' : False,
        'parent_joint' : None,
    },
    'joint2' : {
        'theta_deg' : 30.0,
        'd' : 15.0,
        'a' : 10.0,
        'alpha_deg' : 45.0,
        'theta_variable' : True,
        'd_variable' : False,
        'parent_joint' : "joint1",
    }
}

hand_model = {
    # Nadgarstek (podstawa dłoni)
    'wrist': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 0.0,
        'alpha_deg': 0.0,
        'theta_variable': True,  # rotacja nadgarstka
        'd_variable': False,
        'parent_joint': None,
    },
    
    # ---- KCIUK: propozycja z dwoma zero-length jointami CMC ----
    'thumb_base': {
        # baza - teraz tylko pozycjonowanie i drobny obrót początkowy
        'theta_deg': -25.0,   # lekkie odchylenie z góry (możesz dopasować)
        'd': 5.0,
        'a': 18.0,            # przesunięcie od nadgarstka (rozstaw)
        'alpha_deg': 65.0,     # ustawiamy alpha=0 — orientację zrobią kolejne zero-lengthy
        'theta_variable': False,
        'd_variable': False,
        'parent_joint': 'wrist',
    },

    'thumb_cmc_abd': {
        # zero-length joint - abdukcja/addukcja (ruch na boki)
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 0.0,
        'alpha_deg': 0.0,     # brak tilt — oś obrotu = local Z
        'theta_variable': True,   # sterujemy tym w animacji (odstawienie kciuka)
        'd_variable': False,
        'parent_joint': 'thumb_base',
    },

    'thumb_cmc_flex': {
        # zero-length joint - flexion; tu ustawiamy alpha tak, aby oś zginania była "właściwa"
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 0.0,
        'alpha_deg': 90.0,    # obrót o 90° tak, by następny joint zginął w płaszczyźnie palców
        'theta_variable': True,   # to główny DOF zginania kciuka
        'd_variable': False,
        'parent_joint': 'thumb_cmc_abd',
    },
    'thumb_proximal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 30.0,  # paliczek bliższy
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'thumb_cmc_flex',
    },
    'thumb_distal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 25.0,  # paliczek dalszy
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'thumb_proximal',
    },
    
    # Palec wskazujący
    'index_metacarpal': {
        'theta_deg': -10.0,
        'd': 0.0,
        'a': 60.0,  # długość śródręcza do podstawy palca
        'alpha_deg': 90.0,
        'theta_variable': False,  # śródręcze zwykle nieruchome
        'd_variable': False,
        'parent_joint': 'wrist',
    },
    'index_proximal': {
        'theta_deg': 0.0,
        'theta_limits': [0.0, 50.0],
        'd': 0.0,
        'a': 40.0,  # paliczek bliższy
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'index_metacarpal',
    },
    'index_middle': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 25.0,  # paliczek środkowy
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'index_proximal',
    },
    'index_distal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 20.0,  # paliczek dalszy
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'index_middle',
    },
    
    # Palec środkowy
    'middle_metacarpal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 65.0,
        'alpha_deg': 90.0,
        'theta_variable': False,
        'd_variable': False,
        'parent_joint': 'wrist',
    },
    'middle_proximal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 45.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'middle_metacarpal',
    },
    'middle_middle': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 28.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'middle_proximal',
    },
    'middle_distal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 22.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'middle_middle',
    },
    
    # Palec serdeczny
    'ring_metacarpal': {
        'theta_deg': 10.0,
        'd': 0.0,
        'a': 60.0,
        'alpha_deg': 90.0,
        'theta_variable': False,
        'd_variable': False,
        'parent_joint': 'wrist',
    },
    'ring_proximal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 42.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'ring_metacarpal',
    },
    'ring_middle': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 26.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'ring_proximal',
    },
    'ring_distal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 21.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'ring_middle',
    },
    
    # Mały palec
    'pinky_metacarpal': {
        'theta_deg': 20.0,
        'd': 0.0,
        'a': 55.0,
        'alpha_deg': 90.0,
        'theta_variable': False,
        'd_variable': False,
        'parent_joint': 'wrist',
    },
    'pinky_proximal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 35.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'pinky_metacarpal',
    },
    'pinky_middle': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 20.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'pinky_proximal',
    },
    'pinky_distal': {
        'theta_deg': 0.0,
        'd': 0.0,
        'a': 18.0,
        'alpha_deg': 0.0,
        'theta_variable': True,
        'd_variable': False,
        'parent_joint': 'pinky_middle',
    },
}


# if __name__ == "__main__":
#     import json

#     result = {
#         'meta': {
#             'angle_unit': 'deg',
#             'length_unit': 'mm',
#             'convention': 'classical',
#             'version': '1.0'
#         },
#         'joints': []
#     }

#     for key, value in hand_model.items():
#         joint = {}
#         joint['name'] = key
#         joint['type'] = 'revolute' if value.get('theta_variable',False) else 'prismatic' if value.get('d_variable',False) else 'fixed'
#         joint['parent_joint'] = value.get('parent_joint', None)
#         joint['theta'] = value.get('theta_deg', 0.0)
#         joint['d'] = value.get('d', 0.0)
#         joint['a'] = value.get('a', 0.0)
#         joint['alpha'] = value.get('alpha_deg', 0.0)
#         limits = value.get('theta_limits', None) if joint['type']=='revolute' else value.get('d_limits', None) if joint['type']=='prismatic' else None
#         if limits:
#             joint['limits'] = limits
#         result['joints'].append(joint)
    
#     print(f"{result}")
        
#     json.dump(result, open("hand_model.json","w"), indent=4)

if __name__ == "__main__":
    import json, jsonschema, os
    schema_filename = "dhjoint_schema.json"
    try:
        schema = open(schema_filename).read()
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            schema = open(os.path.join(script_dir, schema_filename)).read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {schema_filename} not found in the current directory or script directory.")

    model_filename = "hand_model.json"
    try:
        model = open(model_filename).read()
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            model = open(os.path.join(script_dir, model_filename)).read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {model_filename} not found in the current directory or script directory.")

    jsonschema.validate(instance=json.loads(model), schema=json.loads(schema))
