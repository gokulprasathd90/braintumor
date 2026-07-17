"""
architectures.py — Keras model factory for all four supported architectures.

Architectures
-------------
- cnn         : Lightweight custom CNN (fast baseline, good for limited compute)
- vgg16       : VGG-16 with ImageNet weights, classification head replaced
- resnet50    : ResNet-50 with ImageNet weights, classification head replaced
- efficientnet: EfficientNetB3 with ImageNet weights (default, best accuracy)

All transfer-learning models use the same two-phase approach:
  Phase 1 — frozen backbone, train only the new classification head
  Phase 2 — unfreeze the top N layers for fine-tuning (called externally
             by setting model.trainable = True selectively)

Usage
-----
    from app.models.architectures import build_model
    model = build_model("efficientnet")
    model.summary()
"""

from __future__ import annotations

from typing import Tuple

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.applications import (
    EfficientNetB3,
    ResNet50,
    VGG16,
)

from app.core.config import settings
from app.core.logging import logger


# ─── Shared head factory ──────────────────────────────────────────────────────

def _classification_head(
    x: tf.Tensor,
    *,
    units: int = 256,
    dropout_rate: float = 0.5,
    l2: float = 1e-4,
    num_classes: int | None = None,
) -> tf.Tensor:
    """
    Dense classification head appended to any backbone.

    Architecture:
        GlobalAveragePooling2D → BatchNorm → Dense(units, relu, L2)
        → Dropout → Dense(num_classes, softmax)
    """
    num_classes = num_classes or settings.num_classes
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.BatchNormalization(name="bn_head")(x)
    x = layers.Dense(
        units,
        activation="relu",
        kernel_regularizer=regularizers.l2(l2),
        name="fc1",
    )(x)
    x = layers.Dropout(dropout_rate, name="dropout_head")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)
    return outputs


# ─── Custom CNN ───────────────────────────────────────────────────────────────

def _build_custom_cnn(
    input_shape: Tuple[int, int, int],
    num_classes: int,
) -> tf.keras.Model:
    """
    Lightweight 4-block CNN for fast experimentation.

    Block structure:
        Conv2D(BN, ReLU) × 2 → MaxPool → Dropout
    Blocks: 32 → 64 → 128 → 256 filters.
    """
    inputs = layers.Input(shape=input_shape, name="input_image")

    # Block 1
    x = layers.Conv2D(32, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv1_1")(inputs)
    x = layers.BatchNormalization(name="bn1_1")(x)
    x = layers.Activation("relu", name="relu1_1")(x)
    x = layers.Conv2D(32, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv1_2")(x)
    x = layers.BatchNormalization(name="bn1_2")(x)
    x = layers.Activation("relu", name="relu1_2")(x)
    x = layers.MaxPooling2D(2, name="pool1")(x)
    x = layers.Dropout(0.25, name="drop1")(x)

    # Block 2
    x = layers.Conv2D(64, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv2_1")(x)
    x = layers.BatchNormalization(name="bn2_1")(x)
    x = layers.Activation("relu", name="relu2_1")(x)
    x = layers.Conv2D(64, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv2_2")(x)
    x = layers.BatchNormalization(name="bn2_2")(x)
    x = layers.Activation("relu", name="relu2_2")(x)
    x = layers.MaxPooling2D(2, name="pool2")(x)
    x = layers.Dropout(0.25, name="drop2")(x)

    # Block 3
    x = layers.Conv2D(128, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv3_1")(x)
    x = layers.BatchNormalization(name="bn3_1")(x)
    x = layers.Activation("relu", name="relu3_1")(x)
    x = layers.Conv2D(128, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv3_2")(x)
    x = layers.BatchNormalization(name="bn3_2")(x)
    x = layers.Activation("relu", name="relu3_2")(x)
    x = layers.MaxPooling2D(2, name="pool3")(x)
    x = layers.Dropout(0.3, name="drop3")(x)

    # Block 4
    x = layers.Conv2D(256, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv4_1")(x)
    x = layers.BatchNormalization(name="bn4_1")(x)
    x = layers.Activation("relu", name="relu4_1")(x)
    x = layers.Conv2D(256, 3, padding="same", kernel_regularizer=regularizers.l2(1e-4), name="conv4_2")(x)
    x = layers.BatchNormalization(name="bn4_2")(x)
    x = layers.Activation("relu", name="relu4_2")(x)
    x = layers.MaxPooling2D(2, name="pool4")(x)
    x = layers.Dropout(0.3, name="drop4")(x)

    # Classification head
    outputs = _classification_head(x, units=512, dropout_rate=0.5, num_classes=num_classes)

    model = models.Model(inputs=inputs, outputs=outputs, name="custom_cnn")
    logger.debug(f"Built custom CNN | input={input_shape} classes={num_classes}")
    return model


# ─── VGG-16 ───────────────────────────────────────────────────────────────────

def _build_vgg16(
    input_shape: Tuple[int, int, int],
    num_classes: int,
) -> tf.keras.Model:
    """VGG-16 backbone (ImageNet weights) with a frozen base and custom head."""
    base = VGG16(
        include_top=False,
        weights="imagenet",
        input_shape=input_shape,
    )
    base.trainable = False  # Phase 1: freeze backbone

    inputs = layers.Input(shape=input_shape, name="input_image")
    x = base(inputs, training=False)
    outputs = _classification_head(x, units=256, dropout_rate=0.5, num_classes=num_classes)

    model = models.Model(inputs=inputs, outputs=outputs, name="vgg16")
    logger.debug(f"Built VGG-16 | input={input_shape} classes={num_classes} frozen_layers={len(base.layers)}")
    return model


# ─── ResNet-50 ────────────────────────────────────────────────────────────────

def _build_resnet50(
    input_shape: Tuple[int, int, int],
    num_classes: int,
) -> tf.keras.Model:
    """ResNet-50 backbone (ImageNet weights) with a frozen base and custom head."""
    base = ResNet50(
        include_top=False,
        weights="imagenet",
        input_shape=input_shape,
    )
    base.trainable = False  # Phase 1: freeze backbone

    inputs = layers.Input(shape=input_shape, name="input_image")
    x = base(inputs, training=False)
    outputs = _classification_head(x, units=256, dropout_rate=0.5, num_classes=num_classes)

    model = models.Model(inputs=inputs, outputs=outputs, name="resnet50")
    logger.debug(f"Built ResNet-50 | input={input_shape} classes={num_classes} frozen_layers={len(base.layers)}")
    return model


# ─── EfficientNet-B3 ──────────────────────────────────────────────────────────

def _build_efficientnet(
    input_shape: Tuple[int, int, int],
    num_classes: int,
) -> tf.keras.Model:
    """
    EfficientNetB3 backbone (ImageNet weights) with a frozen base and custom head.

    EfficientNetB3 expects pixel values in [0, 255] by default; the
    preprocessing module already handles normalisation so we pass a rescaling
    override of 1.0 to skip the built-in rescaling (handled upstream).
    """
    base = EfficientNetB3(
        include_top=False,
        weights="imagenet",
        input_shape=input_shape,
        include_preprocessing=False,  # normalisation done in preprocessing module
    )
    base.trainable = False  # Phase 1: freeze backbone

    inputs = layers.Input(shape=input_shape, name="input_image")
    x = base(inputs, training=False)
    outputs = _classification_head(x, units=512, dropout_rate=0.5, num_classes=num_classes)

    model = models.Model(inputs=inputs, outputs=outputs, name="efficientnet")
    logger.debug(f"Built EfficientNetB3 | input={input_shape} classes={num_classes} frozen_layers={len(base.layers)}")
    return model


# ─── Public factory ───────────────────────────────────────────────────────────

_BUILDERS = {
    "cnn":         _build_custom_cnn,
    "vgg16":       _build_vgg16,
    "resnet50":    _build_resnet50,
    "efficientnet": _build_efficientnet,
}


def build_model(
    model_name: str | None = None,
    *,
    input_shape: Tuple[int, int, int] | None = None,
    num_classes: int | None = None,
    learning_rate: float = 1e-4,
) -> tf.keras.Model:
    """
    Build and compile a Keras model for brain tumour classification.

    Parameters
    ----------
    model_name : str | None
        One of "cnn" | "vgg16" | "resnet50" | "efficientnet".
        Defaults to ``settings.active_model``.
    input_shape : tuple | None
        (H, W, C) — defaults to ``settings.input_shape``.
    num_classes : int | None
        Number of output classes — defaults to ``settings.num_classes``.
    learning_rate : float
        Initial learning rate for the Adam optimiser.

    Returns
    -------
    tf.keras.Model
        Compiled model ready for ``model.fit()``.

    Raises
    ------
    ValueError
        If ``model_name`` is not one of the supported architectures.
    """
    name  = (model_name or settings.active_model).lower()
    shape = input_shape or settings.input_shape
    n_cls = num_classes or settings.num_classes

    if name not in _BUILDERS:
        raise ValueError(
            f"Unknown model '{name}'. "
            f"Choose one of: {list(_BUILDERS.keys())}"
        )

    model = _BUILDERS[name](shape, n_cls)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )

    total_params     = model.count_params()
    trainable_params = sum(tf.size(w).numpy() for w in model.trainable_weights)
    logger.info(
        f"Model compiled | name={name} total_params={total_params:,} "
        f"trainable_params={trainable_params:,} lr={learning_rate}"
    )
    return model


def unfreeze_top_layers(model: tf.keras.Model, n_layers: int = 20) -> tf.keras.Model:
    """
    Unfreeze the last ``n_layers`` of the backbone for fine-tuning (Phase 2).

    Call this after Phase 1 training converges, then re-compile with a
    lower learning rate (e.g. 1e-5).

    Parameters
    ----------
    model : tf.keras.Model
        A model previously returned by ``build_model()``.
    n_layers : int
        Number of layers from the end of the backbone to unfreeze.

    Returns
    -------
    tf.keras.Model
        The same model with modified ``trainable`` flags (not re-compiled).
    """
    # Backbone is the second layer (index 1) for transfer-learning models
    # For the custom CNN every layer is already trainable.
    for layer in model.layers:
        if hasattr(layer, "layers"):  # it's a sub-model (backbone)
            for sub_layer in layer.layers[-n_layers:]:
                if not isinstance(sub_layer, layers.BatchNormalization):
                    sub_layer.trainable = True
            logger.info(f"Unfrozen top {n_layers} layers of backbone '{layer.name}'")
            break
    return model
