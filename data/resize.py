import os
import numpy as np

from tqdm import tqdm
from pathlib import Path
from monai import transforms
import SimpleITK as sitk
from concurrent.futures import ProcessPoolExecutor

def process(mask_path):
    try:
        phase = 'train' if 'train' in mask_path else 'valid'

        # Step 1: Merge class
        relative_path = "/".join(mask_path.split("/")[-3:])
        if Path(f"merged_{phase}_masks/" + relative_path).exists():
            return

        Path(f"merged_{phase}_masks/" + relative_path).parent.mkdir(parents=True, exist_ok=True)

        class_map = {
            1: "spleen",
            2: "kidney_right",
            3: "kidney_left",
            4: "gallbladder",
            5: "liver",
            6: "stomach",
            7: "pancreas",
            8: "adrenal_gland_right",
            9: "adrenal_gland_left",
            10: "lung_upper_lobe_left",
            11: "lung_lower_lobe_left",
            12: "lung_upper_lobe_right",
            13: "lung_middle_lobe_right",
            14: "lung_lower_lobe_right",
            15: "esophagus",
            16: "trachea",
            17: "thyroid_gland",
            18: "small_bowel",
            19: "duodenum",
            20: "colon",
            21: "urinary_bladder",
            22: "prostate",
            23: "kidney_cyst_left",
            24: "kidney_cyst_right",
            25: "sacrum",
            26: "vertebrae_S1",
            27: "vertebrae_L5",
            28: "vertebrae_L4",
            29: "vertebrae_L3",
            30: "vertebrae_L2",
            31: "vertebrae_L1",
            32: "vertebrae_T12",
            33: "vertebrae_T11",
            34: "vertebrae_T10",
            35: "vertebrae_T9",
            36: "vertebrae_T8",
            37: "vertebrae_T7",
            38: "vertebrae_T6",
            39: "vertebrae_T5",
            40: "vertebrae_T4",
            41: "vertebrae_T3",
            42: "vertebrae_T2",
            43: "vertebrae_T1",
            44: "vertebrae_C7",
            45: "vertebrae_C6",
            46: "vertebrae_C5",
            47: "vertebrae_C4",
            48: "vertebrae_C3",
            49: "vertebrae_C2",
            50: "vertebrae_C1",
            51: "heart",
            52: "aorta",
            53: "pulmonary_vein",
            54: "brachiocephalic_trunk",
            55: "subclavian_artery_right",
            56: "subclavian_artery_left",
            57: "common_carotid_artery_right",
            58: "common_carotid_artery_left",
            59: "brachiocephalic_vein_left",
            60: "brachiocephalic_vein_right",
            61: "atrial_appendage_left",
            62: "superior_vena_cava",
            63: "inferior_vena_cava",
            64: "portal_vein_and_splenic_vein",
            65: "iliac_artery_left",
            66: "iliac_artery_right",
            67: "iliac_vena_left",
            68: "iliac_vena_right",
            69: "humerus_left",
            70: "humerus_right",
            71: "scapula_left",
            72: "scapula_right",
            73: "clavicula_left",
            74: "clavicula_right",
            75: "femur_left",
            76: "femur_right",
            77: "hip_left",
            78: "hip_right",
            79: "spinal_cord",
            80: "gluteus_maximus_left",
            81: "gluteus_maximus_right",
            82: "gluteus_medius_left",
            83: "gluteus_medius_right",
            84: "gluteus_minimus_left",
            85: "gluteus_minimus_right",
            86: "autochthon_left",
            87: "autochthon_right",
            88: "iliopsoas_left",
            89: "iliopsoas_right",
            90: "brain",
            91: "skull",
            92: "rib_left_1",
            93: "rib_left_2",
            94: "rib_left_3",
            95: "rib_left_4",
            96: "rib_left_5",
            97: "rib_left_6",
            98: "rib_left_7",
            99: "rib_left_8",
            100: "rib_left_9",
            101: "rib_left_10",
            102: "rib_left_11",
            103: "rib_left_12",
            104: "rib_right_1",
            105: "rib_right_2",
            106: "rib_right_3",
            107: "rib_right_4",
            108: "rib_right_5",
            109: "rib_right_6",
            110: "rib_right_7",
            111: "rib_right_8",
            112: "rib_right_9",
            113: "rib_right_10",
            114: "rib_right_11",
            115: "rib_right_12",
            116: "sternum",
            117: "costal_cartilages",
        }

        merged_organ_id = {
            "lung_upper_lobe_left": 0,
            "lung_lower_lobe_left": 0,
            "lung_upper_lobe_right": 0,
            "lung_middle_lobe_right": 0,
            "lung_lower_lobe_right": 0,
            "heart": 1,
            "atrial_appendage_left": 1,
            "esophagus": 2,
            "aorta": 3,
        }

        mask_ct = sitk.ReadImage(mask_path)
        mask = sitk.GetArrayFromImage(mask_ct)

        fused_mask = np.zeros_like(mask)
        for original_id, organ_name in class_map.items():
            if organ_name not in merged_organ_id:
                continue
            merged_id = merged_organ_id[organ_name]
            fused_mask[mask == original_id] = merged_id + 1

        fused_mask_sitk = sitk.GetImageFromArray(fused_mask)
        fused_mask_sitk.CopyInformation(mask_ct)

        sitk.WriteImage(fused_mask_sitk, f"merged_{phase}_masks/{relative_path}")

        # Step 2: Resize image and mask
        if (
            Path(f"resized_{phase}_images/" + relative_path).exists()
            and Path(f"resized_{phase}_masks/" + relative_path).exists()
        ):
            return

        Path(f"resized_{phase}_images/" + relative_path).parent.mkdir(parents=True, exist_ok=True)
        Path(f"resized_{phase}_masks/" + relative_path).parent.mkdir(parents=True, exist_ok=True)

        image_path = mask_path.replace(f"{phase}_mask", f"{phase}_fixed")
        mask_path = mask_path.replace(f'{phase}_mask', f'merged_{phase}_masks')

        data = {"image": image_path, "label": mask_path}
        res = transforms.LoadImaged(keys=["image", "label"], image_only=False, ensure_channel_first=True)(data)
        image = res["image"]

        affine = res["image_meta_dict"]["affine"]
        spacing = (abs(affine[0, 0].item()), abs(affine[1, 1].item()), abs(affine[2, 2].item()))
        _, h, w, d = image.shape

        ref_spacing = (1.0, 1.0, 3.0)
        scale = [spacing[i] / ref_spacing[i] for i in range(3)]
        target_size = [int(h * scale[1]), int(w * scale[0]), int(d * scale[2])]

        trans = transforms.Compose(
            [
                transforms.Resized(spatial_size=target_size, keys=["image"], mode="trilinear"),
                transforms.Resized(spatial_size=target_size, keys=["label"], mode="nearest"),
                transforms.SaveImaged(
                    output_dir=Path(f"resized_{phase}_images/" + relative_path).parent,
                    keys=["image"],
                    output_postfix="",
                    separate_folder=False,
                    resample=False,
                ),
                transforms.SaveImaged(
                    output_dir=Path(f"resized_{phase}_masks/" + relative_path).parent,
                    keys=["label"],
                    output_postfix="",
                    separate_folder=False,
                    resample=False,
                ),
            ]
        )

        trans(res)

    except Exception as e:
        print(mask_path, e)


if "__main__" == __name__:
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("--split", required=False, default='train', type='str')
    args = parser.parse_args()
    
    split = args.split

    image_root = f'{split}_fix'
    mask_root = f"{split}_mask"

    mask_paths = []
    for root, _, files in os.walk(mask_root):
        for file in files:
            mask_paths.append(os.path.join(root, file))
    
    max_workers = 64
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for _ in tqdm(executor.map(process, mask_paths), total=len(mask_paths)):
            pass
    