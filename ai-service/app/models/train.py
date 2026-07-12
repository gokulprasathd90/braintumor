"""
train.py — Model training placeholder.

This module will contain the full training pipeline once the deep learning
architecture is implemented.  For now it exposes the public function
signatures so the rest of the service can import and wire them without error.

TODO (next phase):
    - Load dataset from dataset/raw/
    - Build augmentation pipeline (ImageDataGenerator / tf.data)
    - Instantiate model architecture from app/models/
    - Compile with Adam + categorical_crossentropy
    - Add callbacks: EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    - Run model.fit() and return training history
    - Persist weights via save_model.py
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def train_model(
    model_name: str = "efficientnet",
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    dataset_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Train a deep learning model on MRI brain tumour images.

    Parameters
    ----------
    model_name : str
        Architecture to train — "cnn" | "vgg16" | "resnet50" | "efficientnet"
    epochs : int
        Maximum number of training epochs.
    batch_size : int
        Mini-batch size.
    learning_rate : float
        Initial learning rate for the Adam optimiser.
    dataset_dir : str | None
        Path to the dataset root.  Uses config default when None.

    Returns
    -------
    dict
        Training history and final metric values.

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    """
    raise NotImplementedError(
        "train_model() is not yet implemented. "
        "Deep learning training will be added in the next phase."
    )
