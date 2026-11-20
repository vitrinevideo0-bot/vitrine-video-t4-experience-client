// Generated from config/T4_CAPTURE_FLOW_V1_0_0.json; do not edit by hand.
export const CAPTURE_FLOW_CONTRACT = {
  "schema_version": "1.0.0",
  "contract_id": "restauration_t4_experience_client_capture_flow_v1_0_0",
  "template_id": "RESTAURATION-T4",
  "template_version": "1.0.0",
  "status": "owner_directed_executable_contract",
  "sources": {
    "guide": {
      "path": "capture-guide/consignes_T4.json",
      "sha256": "1b34521be8cfdc42b8dc30695a499d3d10b9082460a15973133f50ba6e8c4773"
    },
    "questions": {
      "path": "form/questions_T4.json",
      "sha256": "50480389d8052daa66c4cd9f4618115fe84f15ceadc458b2545214b1041de251"
    }
  },
  "counts": {
    "merchant_questions": 6,
    "scenes": 4,
    "states_per_scene": 3,
    "stable_capture_screens": 12
  },
  "scene_durations_ms": [
    6000,
    8000,
    7000,
    9000
  ],
  "transient_states": [
    {
      "id": "COUNTDOWN_3_2_1",
      "counted_in_12_stable_screens": false,
      "sequence": [
        3,
        2,
        1
      ],
      "trigger": "START_RECORDING",
      "then": "B_RECORDING",
      "must_not_be_written_into_capture": true
    }
  ],
  "runtime_rules": {
    "camera_required": true,
    "microphone_requested": true,
    "speech_optional": true,
    "playback_audio_enabled": true,
    "silent_render_audio_enabled": false,
    "source_speed": 1.0,
    "automatic_subtitles": false,
    "retake_deletes_previous_capture": true
  },
  "screens": [
    {
      "scene_id": "S1",
      "scene_index": 1,
      "scene_total": 4,
      "capture_duration_ms": 6000,
      "capture_slot": "captures.S1",
      "ordinal": 1,
      "screen_id": "T4_CAPTURE_S1_A_GUIDE",
      "route_key": "t4.capture.s1.guide",
      "state": "A_GUIDE",
      "purpose": "Faire entrer immédiatement le spectateur dans le lieu et montrer un accueil réel.",
      "bindings": {
        "title": "capture-guide/consignes_T4.json#/scenes/0/titre",
        "instruction": "capture-guide/consignes_T4.json#/scenes/0/consigne",
        "film_list": "capture-guide/consignes_T4.json#/scenes/0/a_filmer",
        "avoid_list": "capture-guide/consignes_T4.json#/scenes/0/a_eviter",
        "required_action": "capture-guide/consignes_T4.json#/scenes/0/ce_que_tu_dois_faire",
        "example": "capture-guide/consignes_T4.json#/scenes/0/exemple_facultatif",
        "primary_action": "capture-guide/consignes_T4.json#/bouton_principal"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 1/4",
        "duration": "6 secondes",
        "title": "BIENVENUE",
        "instruction": "Commence sur l'entrée, l'enseigne ou un repère clair. Avance doucement vers la salle, puis termine sur un sourire ou un geste d'accueil naturel.",
        "film_list": [
          "L'entrée, l'enseigne ou un repère reconnaissable.",
          "Une avancée simple vers l'intérieur.",
          "Une personne consentante qui accueille naturellement."
        ],
        "avoid_list": [
          "Une entrée vide ou trop sombre.",
          "Un contre-jour qui cache le visage.",
          "Un geste exagéré ou une personne non consentante."
        ],
        "required_action": "Dégage le passage, garde le téléphone vertical et termine par une seconde stable sur l'accueil.",
        "voice_note": "Tu peux parler pendant que tu filmes, en français, en fon, en yoruba, en anglais ou dans une autre langue que tu maîtrises.",
        "silence_note": "Tu peux aussi ne pas parler si tu préfères.",
        "optional_example": "Bienvenue chez nous, nous sommes heureux de vous recevoir.",
        "primary_action": "COMMENCER À FILMER"
      },
      "visible_components": [
        "camera_preview_dimmed",
        "scene_progress",
        "instruction_sheet",
        "film_list",
        "avoid_list",
        "consent_note_when_applicable",
        "voice_note",
        "optional_example",
        "start_recording_button"
      ],
      "forbidden_components": [
        "recording_timer",
        "review_actions",
        "automatic_subtitles"
      ],
      "actions": [
        {
          "event": "START_RECORDING",
          "effects": [
            "request_camera_permission",
            "request_microphone_permission",
            "run_COUNTDOWN_3_2_1"
          ],
          "next_screen_id": "T4_CAPTURE_S1_B_RECORDING"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S1_A_GUIDE.png"
    },
    {
      "scene_id": "S1",
      "scene_index": 1,
      "scene_total": 4,
      "capture_duration_ms": 6000,
      "capture_slot": "captures.S1",
      "ordinal": 2,
      "screen_id": "T4_CAPTURE_S1_B_RECORDING",
      "route_key": "t4.capture.s1.recording",
      "state": "B_RECORDING",
      "purpose": "capturer exactement la durée T4, image et microphone à vitesse naturelle",
      "bindings": {
        "elapsed_ms": "runtime.capture.elapsed_ms",
        "progress_0_to_1": "runtime.capture.progress",
        "prompt_timeline": "capture-guide/consignes_T4.json#/scenes/0/recording_prompts",
        "output_uri": "runtime.captures.S1.uri"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 1/4",
        "title": "BIENVENUE",
        "duration_seconds": 6,
        "prompt_timeline": [
          {
            "from_ms": 0,
            "to_ms": 2000,
            "text": "MONTRE L'ENTRÉE"
          },
          {
            "from_ms": 2000,
            "to_ms": 4000,
            "text": "AVANCE VERS L'ACCUEIL"
          },
          {
            "from_ms": 4000,
            "to_ms": 6000,
            "text": "GARDE LE SOURIRE NET"
          }
        ]
      },
      "visible_components": [
        "camera_preview",
        "microphone_active",
        "recording_timer",
        "recording_progress",
        "current_recording_prompt"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "merchant_fields",
        "example_text",
        "manual_stop_button",
        "review_actions",
        "automatic_subtitles"
      ],
      "capture": {
        "starts_after": "COUNTDOWN_3_2_1_COMPLETE",
        "video": true,
        "microphone_audio": true,
        "source_speed": 1.0,
        "source_time_map": "identity",
        "audio_time_map": "identity",
        "duration_ms": 6000,
        "auto_stop": true,
        "manual_stop": false,
        "write_to": "runtime.captures.S1.uri"
      },
      "actions": [
        {
          "event": "CAPTURE_DURATION_REACHED",
          "effects": [
            "stop_recorder",
            "finalize_capture_file",
            "probe_capture_metadata",
            "open_audio_review"
          ],
          "next_screen_id": "T4_CAPTURE_S1_C_REVIEW"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S1_B_RECORDING.png"
    },
    {
      "scene_id": "S1",
      "scene_index": 1,
      "scene_total": 4,
      "capture_duration_ms": 6000,
      "capture_slot": "captures.S1",
      "ordinal": 3,
      "screen_id": "T4_CAPTURE_S1_C_REVIEW",
      "route_key": "t4.capture.s1.review",
      "state": "C_REVIEW",
      "purpose": "relire avec le son, vérifier le contenu et accepter ou refaire la prise",
      "bindings": {
        "preview_uri": "runtime.captures.S1.uri",
        "capture_metadata": "runtime.captures.S1.metadata",
        "review_question": "capture-guide/consignes_T4.json#/scenes/0/review_question",
        "review_checks": "capture-guide/consignes_T4.json#/scenes/0/review_checks",
        "review_error": "capture-guide/consignes_T4.json#/scenes/0/review_error"
      },
      "resolved_text": {
        "take_label": "PRISE 1 · 0:06",
        "review_question": "VOIT-ON CLAIREMENT LE LIEU ET L'ACCUEIL ?",
        "review_checks": [
          "Le lieu se reconnaît dès le début.",
          "La personne est nette et consentante.",
          "La fin est stable."
        ],
        "review_error": "Refais la prise si l'entrée est sombre, coupée ou si l'accueil n'est pas lisible.",
        "redo_action": "REFAIRE",
        "positive_action": "SCÈNE SUIVANTE"
      },
      "visible_components": [
        "captured_video_preview",
        "captured_audio_playback",
        "review_question",
        "review_checklist",
        "redo_button",
        "accept_button"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "recording_timer",
        "recording_progress",
        "automatic_subtitles"
      ],
      "playback": {
        "audio": true,
        "loop": true,
        "source_speed": 1.0
      },
      "actions": [
        {
          "event": "RETAKE",
          "label": "REFAIRE",
          "effects": [
            "delete:runtime.captures.S1",
            "reset_scene_capture_state"
          ],
          "next_screen_id": "T4_CAPTURE_S1_A_GUIDE"
        },
        {
          "event": "ACCEPT_CAPTURE",
          "label": "SCÈNE SUIVANTE",
          "effects": [
            "persist:runtime.captures.S1",
            "mark_capture_accepted"
          ],
          "next_screen_id": "T4_CAPTURE_S2_A_GUIDE"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S1_C_REVIEW.png"
    },
    {
      "scene_id": "S2",
      "scene_index": 2,
      "scene_total": 4,
      "capture_duration_ms": 8000,
      "capture_slot": "captures.S2",
      "ordinal": 4,
      "screen_id": "T4_CAPTURE_S2_A_GUIDE",
      "route_key": "t4.capture.s2.guide",
      "state": "A_GUIDE",
      "purpose": "Montrer la prise en charge, le trajet du plat et sa présentation au client.",
      "bindings": {
        "title": "capture-guide/consignes_T4.json#/scenes/1/titre",
        "instruction": "capture-guide/consignes_T4.json#/scenes/1/consigne",
        "film_list": "capture-guide/consignes_T4.json#/scenes/1/a_filmer",
        "avoid_list": "capture-guide/consignes_T4.json#/scenes/1/a_eviter",
        "required_action": "capture-guide/consignes_T4.json#/scenes/1/ce_que_tu_dois_faire",
        "example": "capture-guide/consignes_T4.json#/scenes/1/exemple_facultatif",
        "primary_action": "capture-guide/consignes_T4.json#/bouton_principal"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 2/4",
        "duration": "8 secondes",
        "title": "LE SERVICE",
        "instruction": "Commence quand le plat est pris en charge, suis-le sur un trajet court, puis garde-le dans le cadre lorsqu'il est posé ou présenté au client.",
        "film_list": [
          "La prise du plat ou le départ du service.",
          "Le déplacement du plat vers la table.",
          "La pose finale avec le plat entièrement visible."
        ],
        "avoid_list": [
          "Couper les mains ou l'assiette.",
          "Faire un trajet long ou encombré.",
          "Laisser une personne traverser devant l'objectif."
        ],
        "required_action": "Reste près de l'action, marche doucement et termine par une pose stable du plat.",
        "voice_note": "Tu peux parler pendant que tu filmes, en français, en fon, en yoruba, en anglais ou dans une autre langue que tu maîtrises.",
        "silence_note": "Tu peux aussi ne pas parler si tu préfères.",
        "optional_example": "Votre commande arrive, préparée et servie avec soin.",
        "primary_action": "COMMENCER À FILMER"
      },
      "visible_components": [
        "camera_preview_dimmed",
        "scene_progress",
        "instruction_sheet",
        "film_list",
        "avoid_list",
        "consent_note_when_applicable",
        "voice_note",
        "optional_example",
        "start_recording_button"
      ],
      "forbidden_components": [
        "recording_timer",
        "review_actions",
        "automatic_subtitles"
      ],
      "actions": [
        {
          "event": "START_RECORDING",
          "effects": [
            "request_camera_permission",
            "request_microphone_permission",
            "run_COUNTDOWN_3_2_1"
          ],
          "next_screen_id": "T4_CAPTURE_S2_B_RECORDING"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S2_A_GUIDE.png"
    },
    {
      "scene_id": "S2",
      "scene_index": 2,
      "scene_total": 4,
      "capture_duration_ms": 8000,
      "capture_slot": "captures.S2",
      "ordinal": 5,
      "screen_id": "T4_CAPTURE_S2_B_RECORDING",
      "route_key": "t4.capture.s2.recording",
      "state": "B_RECORDING",
      "purpose": "capturer exactement la durée T4, image et microphone à vitesse naturelle",
      "bindings": {
        "elapsed_ms": "runtime.capture.elapsed_ms",
        "progress_0_to_1": "runtime.capture.progress",
        "prompt_timeline": "capture-guide/consignes_T4.json#/scenes/1/recording_prompts",
        "output_uri": "runtime.captures.S2.uri"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 2/4",
        "title": "LE SERVICE",
        "duration_seconds": 8,
        "prompt_timeline": [
          {
            "from_ms": 0,
            "to_ms": 2000,
            "text": "CADRE LA PRISE DU PLAT"
          },
          {
            "from_ms": 2000,
            "to_ms": 6000,
            "text": "SUIS LE SERVICE"
          },
          {
            "from_ms": 6000,
            "to_ms": 8000,
            "text": "GARDE LA POSE FINALE"
          }
        ]
      },
      "visible_components": [
        "camera_preview",
        "microphone_active",
        "recording_timer",
        "recording_progress",
        "current_recording_prompt"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "merchant_fields",
        "example_text",
        "manual_stop_button",
        "review_actions",
        "automatic_subtitles"
      ],
      "capture": {
        "starts_after": "COUNTDOWN_3_2_1_COMPLETE",
        "video": true,
        "microphone_audio": true,
        "source_speed": 1.0,
        "source_time_map": "identity",
        "audio_time_map": "identity",
        "duration_ms": 8000,
        "auto_stop": true,
        "manual_stop": false,
        "write_to": "runtime.captures.S2.uri"
      },
      "actions": [
        {
          "event": "CAPTURE_DURATION_REACHED",
          "effects": [
            "stop_recorder",
            "finalize_capture_file",
            "probe_capture_metadata",
            "open_audio_review"
          ],
          "next_screen_id": "T4_CAPTURE_S2_C_REVIEW"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S2_B_RECORDING.png"
    },
    {
      "scene_id": "S2",
      "scene_index": 2,
      "scene_total": 4,
      "capture_duration_ms": 8000,
      "capture_slot": "captures.S2",
      "ordinal": 6,
      "screen_id": "T4_CAPTURE_S2_C_REVIEW",
      "route_key": "t4.capture.s2.review",
      "state": "C_REVIEW",
      "purpose": "relire avec le son, vérifier le contenu et accepter ou refaire la prise",
      "bindings": {
        "preview_uri": "runtime.captures.S2.uri",
        "capture_metadata": "runtime.captures.S2.metadata",
        "review_question": "capture-guide/consignes_T4.json#/scenes/1/review_question",
        "review_checks": "capture-guide/consignes_T4.json#/scenes/1/review_checks",
        "review_error": "capture-guide/consignes_T4.json#/scenes/1/review_error"
      },
      "resolved_text": {
        "take_label": "PRISE 2 · 0:08",
        "review_question": "LE SERVICE SE COMPREND-IL DU DÉBUT À LA FIN ?",
        "review_checks": [
          "La prise du plat est visible.",
          "Le déplacement reste net.",
          "La pose finale montre le plat."
        ],
        "review_error": "Refais la prise si le plat sort du cadre ou si quelqu'un masque l'action.",
        "redo_action": "REFAIRE",
        "positive_action": "SCÈNE SUIVANTE"
      },
      "visible_components": [
        "captured_video_preview",
        "captured_audio_playback",
        "review_question",
        "review_checklist",
        "redo_button",
        "accept_button"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "recording_timer",
        "recording_progress",
        "automatic_subtitles"
      ],
      "playback": {
        "audio": true,
        "loop": true,
        "source_speed": 1.0
      },
      "actions": [
        {
          "event": "RETAKE",
          "label": "REFAIRE",
          "effects": [
            "delete:runtime.captures.S2",
            "reset_scene_capture_state"
          ],
          "next_screen_id": "T4_CAPTURE_S2_A_GUIDE"
        },
        {
          "event": "ACCEPT_CAPTURE",
          "label": "SCÈNE SUIVANTE",
          "effects": [
            "persist:runtime.captures.S2",
            "mark_capture_accepted"
          ],
          "next_screen_id": "T4_CAPTURE_S3_A_GUIDE"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S2_C_REVIEW.png"
    },
    {
      "scene_id": "S3",
      "scene_index": 3,
      "scene_total": 4,
      "capture_duration_ms": 7000,
      "capture_slot": "captures.S3",
      "ordinal": 7,
      "screen_id": "T4_CAPTURE_S3_A_GUIDE",
      "route_key": "t4.capture.s3.guide",
      "state": "A_GUIDE",
      "purpose": "Apporter une preuve humaine avec une vraie bouchée et une réaction naturelle.",
      "bindings": {
        "title": "capture-guide/consignes_T4.json#/scenes/2/titre",
        "instruction": "capture-guide/consignes_T4.json#/scenes/2/consigne",
        "film_list": "capture-guide/consignes_T4.json#/scenes/2/a_filmer",
        "avoid_list": "capture-guide/consignes_T4.json#/scenes/2/a_eviter",
        "required_action": "capture-guide/consignes_T4.json#/scenes/2/ce_que_tu_dois_faire",
        "example": "capture-guide/consignes_T4.json#/scenes/2/exemple_facultatif",
        "primary_action": "capture-guide/consignes_T4.json#/bouton_principal"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 3/4",
        "duration": "7 secondes",
        "title": "LA DÉGUSTATION",
        "instruction": "Cadre ensemble la personne consentante et le plat. Filme une bouchée complète, puis laisse la réaction se produire naturellement sans la faire jouer.",
        "film_list": [
          "Le visage et le plat dans le même cadre.",
          "Une bouchée complète et simple.",
          "Une réaction naturelle avec les yeux et la bouche visibles."
        ],
        "avoid_list": [
          "Demander une fausse réaction ou un faux avis.",
          "Masquer le visage avec une main ou un objet.",
          "Zoomer pendant la bouchée."
        ],
        "required_action": "Obtiens l'accord de la personne, garde le téléphone stable et laisse la réaction respirer à la fin.",
        "voice_note": "Tu peux parler pendant que tu filmes, en français, en fon, en yoruba, en anglais ou dans une autre langue que tu maîtrises.",
        "silence_note": "Tu peux aussi ne pas parler si tu préfères.",
        "optional_example": "Goûte simplement le plat et réagis comme tu le ressens.",
        "primary_action": "COMMENCER À FILMER"
      },
      "visible_components": [
        "camera_preview_dimmed",
        "scene_progress",
        "instruction_sheet",
        "film_list",
        "avoid_list",
        "consent_note_when_applicable",
        "voice_note",
        "optional_example",
        "start_recording_button"
      ],
      "forbidden_components": [
        "recording_timer",
        "review_actions",
        "automatic_subtitles"
      ],
      "actions": [
        {
          "event": "START_RECORDING",
          "effects": [
            "request_camera_permission",
            "request_microphone_permission",
            "run_COUNTDOWN_3_2_1"
          ],
          "next_screen_id": "T4_CAPTURE_S3_B_RECORDING"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S3_A_GUIDE.png"
    },
    {
      "scene_id": "S3",
      "scene_index": 3,
      "scene_total": 4,
      "capture_duration_ms": 7000,
      "capture_slot": "captures.S3",
      "ordinal": 8,
      "screen_id": "T4_CAPTURE_S3_B_RECORDING",
      "route_key": "t4.capture.s3.recording",
      "state": "B_RECORDING",
      "purpose": "capturer exactement la durée T4, image et microphone à vitesse naturelle",
      "bindings": {
        "elapsed_ms": "runtime.capture.elapsed_ms",
        "progress_0_to_1": "runtime.capture.progress",
        "prompt_timeline": "capture-guide/consignes_T4.json#/scenes/2/recording_prompts",
        "output_uri": "runtime.captures.S3.uri"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 3/4",
        "title": "LA DÉGUSTATION",
        "duration_seconds": 7,
        "prompt_timeline": [
          {
            "from_ms": 0,
            "to_ms": 2000,
            "text": "CADRE LE PLAT ET LE VISAGE"
          },
          {
            "from_ms": 2000,
            "to_ms": 4500,
            "text": "FILME LA BOUCHÉE"
          },
          {
            "from_ms": 4500,
            "to_ms": 7000,
            "text": "LAISSE VENIR LA RÉACTION"
          }
        ]
      },
      "visible_components": [
        "camera_preview",
        "microphone_active",
        "recording_timer",
        "recording_progress",
        "current_recording_prompt"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "merchant_fields",
        "example_text",
        "manual_stop_button",
        "review_actions",
        "automatic_subtitles"
      ],
      "capture": {
        "starts_after": "COUNTDOWN_3_2_1_COMPLETE",
        "video": true,
        "microphone_audio": true,
        "source_speed": 1.0,
        "source_time_map": "identity",
        "audio_time_map": "identity",
        "duration_ms": 7000,
        "auto_stop": true,
        "manual_stop": false,
        "write_to": "runtime.captures.S3.uri"
      },
      "actions": [
        {
          "event": "CAPTURE_DURATION_REACHED",
          "effects": [
            "stop_recorder",
            "finalize_capture_file",
            "probe_capture_metadata",
            "open_audio_review"
          ],
          "next_screen_id": "T4_CAPTURE_S3_C_REVIEW"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S3_B_RECORDING.png"
    },
    {
      "scene_id": "S3",
      "scene_index": 3,
      "scene_total": 4,
      "capture_duration_ms": 7000,
      "capture_slot": "captures.S3",
      "ordinal": 9,
      "screen_id": "T4_CAPTURE_S3_C_REVIEW",
      "route_key": "t4.capture.s3.review",
      "state": "C_REVIEW",
      "purpose": "relire avec le son, vérifier le contenu et accepter ou refaire la prise",
      "bindings": {
        "preview_uri": "runtime.captures.S3.uri",
        "capture_metadata": "runtime.captures.S3.metadata",
        "review_question": "capture-guide/consignes_T4.json#/scenes/2/review_question",
        "review_checks": "capture-guide/consignes_T4.json#/scenes/2/review_checks",
        "review_error": "capture-guide/consignes_T4.json#/scenes/2/review_error"
      },
      "resolved_text": {
        "take_label": "PRISE 3 · 0:07",
        "review_question": "LA BOUCHÉE ET LA RÉACTION SONT-ELLES NATURELLES ?",
        "review_checks": [
          "Le visage est net et éclairé.",
          "La bouchée est complète.",
          "La réaction n'est ni masquée ni forcée."
        ],
        "review_error": "Refais la prise si le visage, la bouche ou l'assiette sont coupés.",
        "redo_action": "REFAIRE",
        "positive_action": "SCÈNE SUIVANTE"
      },
      "visible_components": [
        "captured_video_preview",
        "captured_audio_playback",
        "review_question",
        "review_checklist",
        "redo_button",
        "accept_button"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "recording_timer",
        "recording_progress",
        "automatic_subtitles"
      ],
      "playback": {
        "audio": true,
        "loop": true,
        "source_speed": 1.0
      },
      "actions": [
        {
          "event": "RETAKE",
          "label": "REFAIRE",
          "effects": [
            "delete:runtime.captures.S3",
            "reset_scene_capture_state"
          ],
          "next_screen_id": "T4_CAPTURE_S3_A_GUIDE"
        },
        {
          "event": "ACCEPT_CAPTURE",
          "label": "SCÈNE SUIVANTE",
          "effects": [
            "persist:runtime.captures.S3",
            "mark_capture_accepted"
          ],
          "next_screen_id": "T4_CAPTURE_S4_A_GUIDE"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S3_C_REVIEW.png"
    },
    {
      "scene_id": "S4",
      "scene_index": 4,
      "scene_total": 4,
      "capture_duration_ms": 9000,
      "capture_slot": "captures.S4",
      "ordinal": 10,
      "screen_id": "T4_CAPTURE_S4_A_GUIDE",
      "route_key": "t4.capture.s4.guide",
      "state": "A_GUIDE",
      "purpose": "Conclure avec l'ambiance réelle et un cadre stable pour le futur contact.",
      "bindings": {
        "title": "capture-guide/consignes_T4.json#/scenes/3/titre",
        "instruction": "capture-guide/consignes_T4.json#/scenes/3/consigne",
        "film_list": "capture-guide/consignes_T4.json#/scenes/3/a_filmer",
        "avoid_list": "capture-guide/consignes_T4.json#/scenes/3/a_eviter",
        "required_action": "capture-guide/consignes_T4.json#/scenes/3/ce_que_tu_dois_faire",
        "example": "capture-guide/consignes_T4.json#/scenes/3/exemple_facultatif",
        "primary_action": "capture-guide/consignes_T4.json#/bouton_principal"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 4/4",
        "duration": "9 secondes",
        "title": "VENEZ / COMMANDEZ",
        "instruction": "Pars d'un plat ou d'une table, révèle l'ambiance générale, puis ne bouge plus pendant les trois dernières secondes.",
        "film_list": [
          "Un détail appétissant ou une table servie.",
          "La salle, l'équipe ou une ambiance réelle.",
          "Un cadre propre et stable pendant les trois dernières secondes."
        ],
        "avoid_list": [
          "Une caisse ou un espace désordonné.",
          "Une personne reconnaissable sans son accord.",
          "Bouger le téléphone pendant la fin stable."
        ],
        "required_action": "À six secondes, verrouille tes mains et garde exactement le même cadre jusqu'à la fin.",
        "voice_note": "Tu peux parler pendant que tu filmes, en français, en fon, en yoruba, en anglais ou dans une autre langue que tu maîtrises.",
        "silence_note": "Tu peux aussi ne pas parler si tu préfères.",
        "optional_example": "Venez nous retrouver ou commandez directement sur WhatsApp.",
        "primary_action": "COMMENCER À FILMER"
      },
      "visible_components": [
        "camera_preview_dimmed",
        "scene_progress",
        "instruction_sheet",
        "film_list",
        "avoid_list",
        "consent_note_when_applicable",
        "voice_note",
        "optional_example",
        "start_recording_button"
      ],
      "forbidden_components": [
        "recording_timer",
        "review_actions",
        "automatic_subtitles"
      ],
      "actions": [
        {
          "event": "START_RECORDING",
          "effects": [
            "request_camera_permission",
            "request_microphone_permission",
            "run_COUNTDOWN_3_2_1"
          ],
          "next_screen_id": "T4_CAPTURE_S4_B_RECORDING"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S4_A_GUIDE.png"
    },
    {
      "scene_id": "S4",
      "scene_index": 4,
      "scene_total": 4,
      "capture_duration_ms": 9000,
      "capture_slot": "captures.S4",
      "ordinal": 11,
      "screen_id": "T4_CAPTURE_S4_B_RECORDING",
      "route_key": "t4.capture.s4.recording",
      "state": "B_RECORDING",
      "purpose": "capturer exactement la durée T4, image et microphone à vitesse naturelle",
      "bindings": {
        "elapsed_ms": "runtime.capture.elapsed_ms",
        "progress_0_to_1": "runtime.capture.progress",
        "prompt_timeline": "capture-guide/consignes_T4.json#/scenes/3/recording_prompts",
        "output_uri": "runtime.captures.S4.uri"
      },
      "resolved_text": {
        "scene_counter": "SCÈNE 4/4",
        "title": "VENEZ / COMMANDEZ",
        "duration_seconds": 9,
        "prompt_timeline": [
          {
            "from_ms": 0,
            "to_ms": 3000,
            "text": "MONTRE LE PLAT OU LA TABLE"
          },
          {
            "from_ms": 3000,
            "to_ms": 6000,
            "text": "RÉVÈLE L'AMBIANCE"
          },
          {
            "from_ms": 6000,
            "to_ms": 9000,
            "text": "NE BOUGE PLUS"
          }
        ]
      },
      "visible_components": [
        "camera_preview",
        "microphone_active",
        "recording_timer",
        "recording_progress",
        "current_recording_prompt"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "merchant_fields",
        "example_text",
        "manual_stop_button",
        "review_actions",
        "automatic_subtitles"
      ],
      "capture": {
        "starts_after": "COUNTDOWN_3_2_1_COMPLETE",
        "video": true,
        "microphone_audio": true,
        "source_speed": 1.0,
        "source_time_map": "identity",
        "audio_time_map": "identity",
        "duration_ms": 9000,
        "auto_stop": true,
        "manual_stop": false,
        "write_to": "runtime.captures.S4.uri"
      },
      "actions": [
        {
          "event": "CAPTURE_DURATION_REACHED",
          "effects": [
            "stop_recorder",
            "finalize_capture_file",
            "probe_capture_metadata",
            "open_audio_review"
          ],
          "next_screen_id": "T4_CAPTURE_S4_C_REVIEW"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S4_B_RECORDING.png"
    },
    {
      "scene_id": "S4",
      "scene_index": 4,
      "scene_total": 4,
      "capture_duration_ms": 9000,
      "capture_slot": "captures.S4",
      "ordinal": 12,
      "screen_id": "T4_CAPTURE_S4_C_REVIEW",
      "route_key": "t4.capture.s4.review",
      "state": "C_REVIEW",
      "purpose": "relire avec le son, vérifier le contenu et accepter ou refaire la prise",
      "bindings": {
        "preview_uri": "runtime.captures.S4.uri",
        "capture_metadata": "runtime.captures.S4.metadata",
        "review_question": "capture-guide/consignes_T4.json#/scenes/3/review_question",
        "review_checks": "capture-guide/consignes_T4.json#/scenes/3/review_checks",
        "review_error": "capture-guide/consignes_T4.json#/scenes/3/review_error"
      },
      "resolved_text": {
        "take_label": "PRISE 4 · 0:09",
        "review_question": "LA FIN RESTE-T-ELLE STABLE PENDANT TROIS SECONDES ?",
        "review_checks": [
          "Le plat ou l'ambiance donne envie.",
          "Toutes les personnes visibles sont consentantes.",
          "Les trois dernières secondes sont stables."
        ],
        "review_error": "Refais la prise si le téléphone bouge pendant les trois dernières secondes.",
        "redo_action": "REFAIRE",
        "positive_action": "VOIR MON MONTAGE"
      },
      "visible_components": [
        "captured_video_preview",
        "captured_audio_playback",
        "review_question",
        "review_checklist",
        "redo_button",
        "accept_button"
      ],
      "forbidden_components": [
        "instruction_sheet",
        "recording_timer",
        "recording_progress",
        "automatic_subtitles"
      ],
      "playback": {
        "audio": true,
        "loop": true,
        "source_speed": 1.0
      },
      "actions": [
        {
          "event": "RETAKE",
          "label": "REFAIRE",
          "effects": [
            "delete:runtime.captures.S4",
            "reset_scene_capture_state"
          ],
          "next_screen_id": "T4_CAPTURE_S4_A_GUIDE"
        },
        {
          "event": "ACCEPT_CAPTURE",
          "label": "VOIR MON MONTAGE",
          "effects": [
            "persist:runtime.captures.S4",
            "mark_capture_accepted"
          ],
          "next_screen_id": "T4_RENDER_CONFIRMATION"
        }
      ],
      "proof_png": "ui-screens/T4_CAPTURE_S4_C_REVIEW.png"
    }
  ],
  "session_model": {
    "name": "T4ExperienceClientSession",
    "fields": [
      "merchant_payload",
      "captures",
      "current_screen_id",
      "accepted_scene_ids"
    ],
    "persistence": "persist accepted content URIs and probed media metadata until RenderJob submission"
  },
  "renderer_handoff": {
    "trigger": "ACCEPT_CAPTURE on T4_CAPTURE_S4_C_REVIEW",
    "render_job": "demo/render_job_silent_demo.json",
    "template_contract": "config/T4_EXPERIENCE_CLIENT_TEMPLATE_V1_0_0.json",
    "capture_bindings": {
      "captures.S1": "runtime.captures.S1.uri",
      "captures.S2": "runtime.captures.S2.uri",
      "captures.S3": "runtime.captures.S3.uri",
      "captures.S4": "runtime.captures.S4.uri"
    },
    "merchant_payload_source": "form/questions_T4.json",
    "production_render_plane": "github_actions",
    "cloudflare_rendering_forbidden": true
  }
} as const;
