"""File path constants for movement and rest images used in the exercise app.

This module defines the `Images` class, which stores lists of paths
to PNG files representing hand/wrist movements for sets A and B,
as well as the path to the rest image.
"""

class Images:
    """Container for static file paths of movement and rest images.

    Attributes:
        MOVEMENT_IMAGES_A (list[str]): Paths to movement images for exercise set A.
        MOVEMENT_IMAGES_B (list[str]): Paths to movement images for exercise set B.
        REST (str): Path to the rest image.
    """

    MOVEMENT_IMAGES_A = [
        "movement_library/EA/Index_flexion_M1.png",
        "movement_library/EA/Index_Extension_M2.png",
        "movement_library/EA/Middle_Flexion_M3.png",
        "movement_library/EA/Middle_Extension_M4.png",
        "movement_library/EA/Ring_Flexion_M5.png",
        "movement_library/EA/Ring_Extension_M6.png",
        "movement_library/EA/Little_Flexion_M7.png",
        "movement_library/EA/Little_Extension_M8.png",
        "movement_library/EA/Thurmb_Adduction_M9.png",
        "movement_library/EA/Thurmb_Abduction_M10.png",
        "movement_library/EA/Thurmb_Flexion_M11.png",
        "movement_library/EA/Thurmb_Extension_M12.png"
    ]
    MOVEMENT_IMAGES_B = [
        "movement_library/EB/Thrumb_up_M13.png",
        "movement_library/EB/Extension_of_index_and_middle_M14.PNG.png",
        "movement_library/EB/Flexion_of_little_and_ring_M15.PNG.png",
        "movement_library/EB/Thumb_opposing_of base_of_little_finger_M16.PNG.png",
        "movement_library/EB/hands_open_M17.PNG.png",
        "movement_library/EB/Fingures_fixed_together_in_fist_M18.PNG.png",
        "movement_library/EB/pointing_index_M19.PNG.png",
        "movement_library/EB/adduction_of_extended_fingers_M20.PNG.png",
        "movement_library/EB/wrist_supination_middile_finger_M21.PNG.png",
        "movement_library/EB/wrist_pronation_M22.PNG.png",
        "movement_library/EB/wrist_supination_little_finger_M23.PNG.png",
        "movement_library/EB/wrist_pronation_little_finger_M24.PNG.png",
        "movement_library/EB/wrist_flexion_M25.PNG.png",
        "movement_library/EB/wrist_extension_M26.PNG.png",
        "movement_library/EB/wrist_radial_deviation_M27.PNG.png",
        "movement_library/EB/wrist_ular_deviation_M28.PNG.png",
        "movement_library/EB/wrist_extension_with_closed_hand_M29.PNG.png"
    ]

    REST = "movement_library/Rest_M0.png"