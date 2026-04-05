from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from lexer import LexError, LineTokens, lex


class MLError(Exception):
    pass


def _unquote(tok: str) -> str:
    if len(tok) >= 2 and tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    return tok


def _require_quoted(tok: str, *, what: str, line_no: int) -> str:
    if not (len(tok) >= 2 and tok.startswith('"') and tok.endswith('"')):
        raise MLError(f'Oops! {what} must be in quotes on line {line_no}.')
    return _unquote(tok)


def _require_int(tok: str, *, what: str, line_no: int) -> int:
    try:
        return int(_unquote(tok))
    except ValueError as e:
        raise MLError(f"Oops! {what} must be a number on line {line_no}.") from e


def _require_float(tok: str, *, what: str, line_no: int) -> float:
    try:
        return float(_unquote(tok))
    except ValueError as e:
        raise MLError(f"Oops! {what} must be a number on line {line_no}.") from e


def _require_ml_deps() -> tuple[Any, Any, Any, Any, Any]:
    missing: list[str] = []
    try:
        import numpy as np
    except ModuleNotFoundError:
        np = None
        missing.append("numpy")

    try:
        import pandas as pd
    except ModuleNotFoundError:
        pd = None
        missing.append("pandas")

    try:
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        from sklearn.metrics import accuracy_score
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.linear_model import LinearRegression
    except ModuleNotFoundError:
        train_test_split = None
        StandardScaler = None
        LabelEncoder = None
        accuracy_score = None
        RandomForestClassifier = None
        DecisionTreeClassifier = None
        LinearRegression = None
        missing.append("scikit-learn")

    try:
        from tensorflow import keras
    except ModuleNotFoundError:
        keras = None
        missing.append("tensorflow")

    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        plt = None
        missing.append("matplotlib")

    if missing:
        pkgs = " ".join(sorted(set(missing)))
        raise MLError(
            "Missing ML dependencies: "
            + pkgs
            + ". Install them and try again."
            + " Example: pip install "
            + pkgs
        )

    # sklearn symbols
    skl = {
        "train_test_split": train_test_split,
        "StandardScaler": StandardScaler,
        "LabelEncoder": LabelEncoder,
        "accuracy_score": accuracy_score,
        "RandomForestClassifier": RandomForestClassifier,
        "DecisionTreeClassifier": DecisionTreeClassifier,
        "LinearRegression": LinearRegression,
    }

    return np, pd, skl, keras, plt


@dataclass
class MLState:
    base_dir: Path

    # data
    df: Any = None
    feature_cols: list[str] = field(default_factory=list)
    label_col: Optional[str] = None

    X: Any = None
    y: Any = None
    X_train: Any = None
    X_test: Any = None
    y_train: Any = None
    y_test: Any = None

    scaler: Any = None
    label_encoder: Any = None

    # neural network
    nn_name: Optional[str] = None
    nn_layers: list[dict[str, Any]] = field(default_factory=list)
    learning_rate: float = 0.001
    epochs: int = 10
    batch_size: int = 32
    keras_model: Any = None
    last_history: Any = None
    last_eval: dict[str, float] = field(default_factory=dict)

    # classic ML
    classic_model: Any = None
    classic_model_kind: Optional[str] = None

    # matrices
    matrices: dict[str, Any] = field(default_factory=dict)
    current_matrix: Optional[str] = None

    # plots
    plt: Any = None
    last_plot_path: Optional[Path] = None


def _ensure_data_loaded(st: MLState, *, line_no: int) -> None:
    if st.df is None and st.X is None:
        raise MLError(f"Oops! No data loaded yet (line {line_no}). Use: load data from \"file.csv\"")


def _infer_xy_from_df(st: MLState) -> None:
    # Heuristic: last column is label
    cols = list(st.df.columns)
    if not cols:
        raise MLError("Oops! Data has no columns.")
    st.label_col = cols[-1]
    st.feature_cols = cols[:-1]


def _build_nn(st: MLState, *, keras: Any, np: Any) -> Any:
    if not st.nn_layers:
        raise MLError("Oops! Neural network has no layers. Add layers first.")

    input_layer = st.nn_layers[0]
    if input_layer.get("type") != "input":
        raise MLError("Oops! First layer must be an input layer.")

    input_neurons = int(input_layer["neurons"])

    model = keras.Sequential()

    first_dense_added = False
    for layer in st.nn_layers:
        t = layer.get("type")
        if t == "input":
            continue
        if t in ("hidden", "output"):
            neurons = int(layer["neurons"])
            activation = str(layer.get("activation") or "relu")
            if not first_dense_added:
                model.add(keras.layers.Dense(neurons, activation=activation, input_shape=(input_neurons,)))
                first_dense_added = True
            else:
                model.add(keras.layers.Dense(neurons, activation=activation))
            continue
        raise MLError("Oops! Unknown layer type.")

    opt = keras.optimizers.Adam(learning_rate=st.learning_rate)

    # Choose loss based on label shape
    loss = "sparse_categorical_crossentropy"
    metrics = ["accuracy"]

    model.compile(optimizer=opt, loss=loss, metrics=metrics)
    return model


def _prepare_xy(st: MLState, *, np: Any, skl: Any) -> None:
    if st.df is None:
        raise MLError("Oops! No data loaded.")

    if not st.feature_cols or st.label_col is None:
        _infer_xy_from_df(st)

    X = st.df[st.feature_cols].to_numpy()
    y_raw = st.df[st.label_col].to_numpy()

    # Encode labels if needed
    if st.label_encoder is None:
        st.label_encoder = skl["LabelEncoder"]()
        try:
            y = st.label_encoder.fit_transform(y_raw)
        except Exception:
            # if already numeric
            y = y_raw
    else:
        y = st.label_encoder.transform(y_raw)

    st.X = X
    st.y = y


def _cmd_load_data(st: MLState, lt: LineTokens, *, pd: Any) -> None:
    # load data from "file.csv"
    toks = lt.tokens
    if len(toks) != 4 or toks[:3] != ["load", "data", "from"]:
        raise MLError(f"Invalid load data command on line {lt.line_no}.")

    path = _require_quoted(toks[3], what="File path", line_no=lt.line_no)
    full = (st.base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    print(f"loading data from: {full}")
    if not full.exists():
        raise MLError(f"File not found: {path} (line {lt.line_no}).")

    if full.suffix.lower() == ".csv":
        st.df = pd.read_csv(full)
    elif full.suffix.lower() == ".json":
        st.df = pd.read_json(full)
    else:
        raise MLError(f"Unsupported data file type: {full.suffix} (line {lt.line_no}).")

    st.feature_cols = []
    st.label_col = None
    st.X = None
    st.y = None
    st.X_train = None
    st.X_test = None
    st.y_train = None
    st.y_test = None


def _cmd_show_data_info(st: MLState) -> None:
    _ensure_data_loaded(st, line_no=0)
    if st.df is None:
        raise MLError("Oops! Data info is only available for loaded table data.")
    print("--- data info ---")
    print(st.df.info())


def _cmd_show_data_shape(st: MLState) -> None:
    _ensure_data_loaded(st, line_no=0)
    if st.df is None:
        raise MLError("Oops! Data shape is only available for loaded table data.")
    print("data shape:", st.df.shape)


def _cmd_normalize_data(st: MLState, *, skl: Any) -> None:
    _ensure_data_loaded(st, line_no=0)
    if st.df is None:
        raise MLError("Oops! normalize data needs loaded table data.")

    _infer_xy_from_df(st)
    scaler = skl["StandardScaler"]()
    st.df[st.feature_cols] = scaler.fit_transform(st.df[st.feature_cols].to_numpy())
    st.scaler = scaler


def _cmd_split_data(st: MLState, lt: LineTokens, *, np: Any, skl: Any) -> None:
    # split data into training 80 and testing 20
    toks = lt.tokens
    if len(toks) != 8 or toks[:3] != ["split", "data", "into"]:
        raise MLError(f"Invalid split data command on line {lt.line_no}.")
    if toks[3] != "training":
        raise MLError(f"Invalid split data command on line {lt.line_no}.")
    if toks[5] != "and" or toks[6] != "testing":
        raise MLError(f"Invalid split data command on line {lt.line_no}.")

    train_pct = _require_int(toks[4], what="training percent", line_no=lt.line_no)
    test_pct = _require_int(toks[7], what="testing percent", line_no=lt.line_no)
    if train_pct + test_pct != 100:
        raise MLError(f"Oops! training percent + testing percent must equal 100 (line {lt.line_no}).")

    _prepare_xy(st, np=np, skl=skl)

    test_size = test_pct / 100.0
    st.X_train, st.X_test, st.y_train, st.y_test = skl["train_test_split"](
        st.X,
        st.y,
        test_size=test_size,
        random_state=42,
        stratify=st.y,
    )


def _cmd_create_neural_network(st: MLState, lt: LineTokens) -> None:
    # create neural network "MyAI"
    toks = lt.tokens
    if len(toks) != 4 or toks[:3] != ["create", "neural", "network"]:
        raise MLError(f"Invalid create neural network on line {lt.line_no}.")
    st.nn_name = _require_quoted(toks[3], what="Neural network name", line_no=lt.line_no)
    st.nn_layers = []
    st.keras_model = None
    st.last_history = None
    st.last_eval = {}


def _cmd_add_layer(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens

    # add input layer 4 neurons
    if toks[:3] == ["add", "input", "layer"]:
        if len(toks) != 5 or toks[4] != "neurons":
            raise MLError(f"Invalid input layer on line {lt.line_no}.")
        neurons = _require_int(toks[3], what="neurons", line_no=lt.line_no)
        st.nn_layers.append({"type": "input", "neurons": neurons})
        return

    # add hidden layer 8 neurons activation "relu"
    if toks[:3] == ["add", "hidden", "layer"]:
        if len(toks) != 7 or toks[4] != "neurons" or toks[5] != "activation":
            raise MLError(f"Invalid hidden layer on line {lt.line_no}.")
        neurons = _require_int(toks[3], what="neurons", line_no=lt.line_no)
        activation = _require_quoted(toks[6], what="Activation", line_no=lt.line_no)
        st.nn_layers.append({"type": "hidden", "neurons": neurons, "activation": activation})
        return

    # add output layer 3 neurons activation "softmax"
    if toks[:3] == ["add", "output", "layer"]:
        if len(toks) != 7 or toks[4] != "neurons" or toks[5] != "activation":
            raise MLError(f"Invalid output layer on line {lt.line_no}.")
        neurons = _require_int(toks[3], what="neurons", line_no=lt.line_no)
        activation = _require_quoted(toks[6], what="Activation", line_no=lt.line_no)
        st.nn_layers.append({"type": "output", "neurons": neurons, "activation": activation})
        return

    raise MLError(f"Oops! I don't understand this layer command on line {lt.line_no}.")


def _cmd_set_hyperparam(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens

    # set learning rate to 0.001
    if toks[:3] == ["set", "learning", "rate"]:
        if len(toks) != 5 or toks[3] != "to":
            raise MLError(f"Invalid set learning rate on line {lt.line_no}.")
        st.learning_rate = _require_float(toks[4], what="learning rate", line_no=lt.line_no)
        return

    # set epochs to 50
    if toks[:2] == ["set", "epochs"]:
        if len(toks) != 4 or toks[2] != "to":
            raise MLError(f"Invalid set epochs on line {lt.line_no}.")
        st.epochs = _require_int(toks[3], what="epochs", line_no=lt.line_no)
        return

    # set batch size to 32
    if toks[:3] == ["set", "batch", "size"]:
        if len(toks) != 5 or toks[3] != "to":
            raise MLError(f"Invalid set batch size on line {lt.line_no}.")
        st.batch_size = _require_int(toks[4], what="batch size", line_no=lt.line_no)
        return

    raise MLError(f"Oops! I don't understand '{toks[0]}' on line {lt.line_no}.")


def _cmd_train_model(st: MLState, lt: LineTokens, *, np: Any, skl: Any, keras: Any) -> None:
    # train model on training data
    toks = lt.tokens
    if toks != ["train", "model", "on", "training", "data"]:
        raise MLError(f"Invalid train command on line {lt.line_no}.")

    if st.X_train is None or st.y_train is None:
        raise MLError(f"Oops! Split your data first (line {lt.line_no}).")

    st.keras_model = _build_nn(st, keras=keras, np=np)

    # Ensure y is int for sparse_categorical_crossentropy
    y_train = st.y_train
    y_test = st.y_test

    history = st.keras_model.fit(
        st.X_train,
        y_train,
        epochs=st.epochs,
        batch_size=st.batch_size,
        validation_data=(st.X_test, y_test),
        verbose=1,
    )
    st.last_history = history

    loss, acc = st.keras_model.evaluate(st.X_test, y_test, verbose=0)
    st.last_eval = {"loss": float(loss), "accuracy": float(acc)}


def _cmd_show_metric(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens
    if toks == ["show", "accuracy"]:
        if "accuracy" not in st.last_eval:
            raise MLError(f"Oops! No accuracy yet (line {lt.line_no}). Train first.")
        print("accuracy:", st.last_eval["accuracy"])
        return
    if toks == ["show", "loss"]:
        if "loss" not in st.last_eval:
            raise MLError(f"Oops! No loss yet (line {lt.line_no}). Train first.")
        print("loss:", st.last_eval["loss"])
        return
    if toks == ["show", "training", "progress"]:
        if st.last_history is None:
            raise MLError(f"Oops! No training progress yet (line {lt.line_no}). Train first.")
        hist = st.last_history.history
        # Print last epoch values
        last_epoch = len(next(iter(hist.values()))) - 1 if hist else 0
        out = {k: float(v[last_epoch]) for k, v in hist.items() if v}
        print("training progress:", out)
        return

    raise MLError(f"Oops! I don't understand '{toks[0]}' on line {lt.line_no}.")


def _cmd_save_model(st: MLState, lt: LineTokens) -> None:
    # save model as "myai.model"
    toks = lt.tokens
    if len(toks) != 4 or toks[:3] != ["save", "model", "as"]:
        raise MLError(f"Invalid save model on line {lt.line_no}.")
    if st.keras_model is None:
        raise MLError(f"Oops! No neural network model to save (line {lt.line_no}).")
    name = _require_quoted(toks[3], what="Model filename", line_no=lt.line_no)
    requested = st.base_dir / name

    # Keras 3 requires a .keras or .h5 file for model.save().
    # Keep ReadCode syntax stable by mapping unknown extensions (like .model) to .keras.
    if requested.suffix.lower() not in (".keras", ".h5"):
        out = Path(str(requested) + ".keras")
    else:
        out = requested

    st.keras_model.save(out)
    if out != requested:
        print(f"saved model: {requested} (stored as {out.name})")
    else:
        print(f"saved model: {out}")


def _cmd_load_model(st: MLState, lt: LineTokens, *, keras: Any) -> None:
    # load model from "myai.model"
    toks = lt.tokens
    if len(toks) != 4 or toks[:3] != ["load", "model", "from"]:
        raise MLError(f"Invalid load model on line {lt.line_no}.")
    name = _require_quoted(toks[3], what="Model filename", line_no=lt.line_no)
    requested = st.base_dir / name

    candidates = [requested]
    if requested.suffix.lower() not in (".keras", ".h5"):
        candidates.append(Path(str(requested) + ".keras"))
        candidates.append(Path(str(requested) + ".h5"))

    found: Optional[Path] = None
    for c in candidates:
        if c.exists():
            found = c
            break

    if found is None:
        raise MLError(f"Model file not found: {name} (line {lt.line_no}).")

    st.keras_model = keras.models.load_model(found)
    if found != requested:
        print(f"loaded model: {requested} (loaded from {found.name})")
    else:
        print(f"loaded model: {found}")


def _cmd_predict_model(st: MLState, lt: LineTokens, *, np: Any) -> None:
    # predict using model on testing data
    toks = lt.tokens
    if toks != ["predict", "using", "model", "on", "testing", "data"]:
        raise MLError(f"Invalid predict command on line {lt.line_no}.")
    if st.keras_model is None:
        raise MLError(f"Oops! No model to predict with (line {lt.line_no}).")
    if st.X_test is None:
        raise MLError(f"Oops! No testing data (line {lt.line_no}).")

    preds = st.keras_model.predict(st.X_test, verbose=0)
    st.last_eval["predictions_count"] = float(len(preds))
    st._last_predictions = preds  # type: ignore[attr-defined]


def _cmd_show_predictions(st: MLState, lt: LineTokens, *, np: Any) -> None:
    toks = lt.tokens
    if toks != ["show", "predictions"]:
        raise MLError(f"Invalid show predictions on line {lt.line_no}.")
    preds = getattr(st, "_last_predictions", None)
    if preds is None:
        raise MLError(f"Oops! No predictions yet (line {lt.line_no}).")
    # Print first 5
    shown = preds[:5]
    print("predictions (first 5):")
    print(shown)


def _cmd_show_model_accuracy(st: MLState, lt: LineTokens, *, np: Any, skl: Any) -> None:
    toks = lt.tokens
    if toks != ["show", "model", "accuracy"]:
        raise MLError(f"Invalid show model accuracy on line {lt.line_no}.")
    preds = getattr(st, "_last_predictions", None)
    if preds is None:
        raise MLError(f"Oops! No predictions yet (line {lt.line_no}).")
    if st.y_test is None:
        raise MLError(f"Oops! No testing labels (line {lt.line_no}).")

    y_pred = preds.argmax(axis=1)
    acc = skl["accuracy_score"](st.y_test, y_pred)
    print("model accuracy:", float(acc))


def _cmd_create_matrix(st: MLState, lt: LineTokens, *, np: Any) -> None:
    # create matrix 3 by 3
    toks = lt.tokens
    if len(toks) != 5 or toks[:2] != ["create", "matrix"] or toks[3] != "by":
        raise MLError(f"Invalid create matrix on line {lt.line_no}.")
    rows = _require_int(toks[2], what="rows", line_no=lt.line_no)
    cols = _require_int(toks[4], what="cols", line_no=lt.line_no)
    name = "matrix"
    st.matrices[name] = np.zeros((rows, cols), dtype=float)
    st.current_matrix = name


def _cmd_set_matrix_values(st: MLState, lt: LineTokens, *, np: Any) -> None:
    # set matrix values to 1 2 3 ...
    toks = lt.tokens
    if len(toks) < 5 or toks[:3] != ["set", "matrix", "values"] or toks[3] != "to":
        raise MLError(f"Invalid set matrix values on line {lt.line_no}.")
    if not st.current_matrix:
        raise MLError(f"Oops! No matrix created yet (line {lt.line_no}).")
    m = st.matrices.get(st.current_matrix)
    if m is None:
        raise MLError(f"Oops! No matrix available (line {lt.line_no}).")

    vals = [float(_unquote(t)) for t in toks[4:]]
    if len(vals) != m.size:
        raise MLError(
            f"Oops! You gave {len(vals)} values but the matrix needs {m.size} values (line {lt.line_no})."
        )
    st.matrices[st.current_matrix] = np.array(vals, dtype=float).reshape(m.shape)


def _cmd_show_matrix(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens
    if len(toks) != 3 or toks[:2] != ["show", "matrix"]:
        raise MLError(f"Invalid show matrix on line {lt.line_no}.")
    name = toks[2]
    if name not in st.matrices:
        raise MLError(f"Oops! Matrix '{name}' not found (line {lt.line_no}).")
    print(f"matrix {name}:")
    print(st.matrices[name])


def _cmd_transpose_matrix(st: MLState, lt: LineTokens, *, np: Any) -> None:
    toks = lt.tokens
    if len(toks) != 3 or toks[:2] != ["transpose", "matrix"]:
        raise MLError(f"Invalid transpose matrix on line {lt.line_no}.")
    name = toks[2]
    if name not in st.matrices:
        raise MLError(f"Oops! Matrix '{name}' not found (line {lt.line_no}).")
    st.matrices[name] = st.matrices[name].T


def _cmd_add_multiply_matrix(st: MLState, lt: LineTokens, *, np: Any) -> None:
    toks = lt.tokens
    if len(toks) != 6 or toks[2] != "matrix" or toks[4] != "with" or toks[5] == "matrix":
        raise MLError(f"Invalid matrix operation on line {lt.line_no}.")


def _cmd_create_classifier_regressor(st: MLState, lt: LineTokens, *, skl: Any) -> None:
    toks = lt.tokens
    # create classifier "random forest"
    if toks[:2] == ["create", "classifier"] and len(toks) == 3:
        kind = _require_quoted(toks[2], what="Classifier type", line_no=lt.line_no).lower()
        if kind == "random forest":
            st.classic_model = skl["RandomForestClassifier"](n_estimators=200, random_state=42)
            st.classic_model_kind = kind
            return
        if kind == "decision tree":
            st.classic_model = skl["DecisionTreeClassifier"](random_state=42)
            st.classic_model_kind = kind
            return
        raise MLError(f"Unsupported classifier '{kind}' (line {lt.line_no}).")

    # create regressor "linear regression"
    if toks[:2] == ["create", "regressor"] and len(toks) == 3:
        kind = _require_quoted(toks[2], what="Regressor type", line_no=lt.line_no).lower()
        if kind == "linear regression":
            st.classic_model = skl["LinearRegression"]()
            st.classic_model_kind = kind
            return
        raise MLError(f"Unsupported regressor '{kind}' (line {lt.line_no}).")

    raise MLError(f"Oops! Invalid classic ML model command on line {lt.line_no}.")


def _cmd_fit_classifier(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens
    if toks != ["fit", "classifier", "on", "training", "data"]:
        raise MLError(f"Invalid fit classifier on line {lt.line_no}.")
    if st.classic_model is None:
        raise MLError(f"Oops! No classifier created yet (line {lt.line_no}).")
    if st.X_train is None or st.y_train is None:
        raise MLError(f"Oops! Split your data first (line {lt.line_no}).")
    st.classic_model.fit(st.X_train, st.y_train)


def _cmd_predict_classifier(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens
    if toks != ["predict", "using", "classifier", "on", "testing", "data"]:
        raise MLError(f"Invalid predict classifier on line {lt.line_no}.")
    if st.classic_model is None:
        raise MLError(f"Oops! No classifier created yet (line {lt.line_no}).")
    if st.X_test is None:
        raise MLError(f"Oops! No testing data (line {lt.line_no}).")
    st._classic_predictions = st.classic_model.predict(st.X_test)  # type: ignore[attr-defined]


def _cmd_show_classifier_accuracy(st: MLState, lt: LineTokens, *, skl: Any) -> None:
    toks = lt.tokens
    if toks != ["show", "classifier", "accuracy"]:
        raise MLError(f"Invalid show classifier accuracy on line {lt.line_no}.")
    preds = getattr(st, "_classic_predictions", None)
    if preds is None:
        raise MLError(f"Oops! No classifier predictions yet (line {lt.line_no}).")
    if st.y_test is None:
        raise MLError(f"Oops! No testing labels (line {lt.line_no}).")
    acc = skl["accuracy_score"](st.y_test, preds)
    print("classifier accuracy:", float(acc))


def _cmd_plot(st: MLState, lt: LineTokens, *, plt: Any) -> None:
    toks = lt.tokens

    if toks == ["plot", "training", "loss"]:
        if st.last_history is None:
            raise MLError(f"Oops! No training history yet (line {lt.line_no}).")
        hist = st.last_history.history
        if "loss" not in hist:
            raise MLError(f"Oops! Loss not available (line {lt.line_no}).")
        plt.figure()
        plt.plot(hist["loss"], label="loss")
        if "val_loss" in hist:
            plt.plot(hist["val_loss"], label="val_loss")
        plt.title("Training Loss")
        plt.legend()
        st.plt = plt
        return

    if toks == ["plot", "accuracy", "graph"]:
        if st.last_history is None:
            raise MLError(f"Oops! No training history yet (line {lt.line_no}).")
        hist = st.last_history.history
        if "accuracy" not in hist:
            raise MLError(f"Oops! Accuracy not available (line {lt.line_no}).")
        plt.figure()
        plt.plot(hist["accuracy"], label="accuracy")
        if "val_accuracy" in hist:
            plt.plot(hist["val_accuracy"], label="val_accuracy")
        plt.title("Accuracy")
        plt.legend()
        st.plt = plt
        return

    # plot data "col1" vs "col2"
    if len(toks) == 6 and toks[:2] == ["plot", "data"] and toks[3] == "vs":
        if st.df is None:
            raise MLError(f"Oops! No data loaded (line {lt.line_no}).")
        c1 = _require_quoted(toks[2], what="Column", line_no=lt.line_no)
        c2 = _require_quoted(toks[4], what="Column", line_no=lt.line_no)
        if c1 not in st.df.columns or c2 not in st.df.columns:
            raise MLError(f"Oops! Column not found (line {lt.line_no}).")
        plt.figure()
        plt.scatter(st.df[c1], st.df[c2])
        plt.xlabel(c1)
        plt.ylabel(c2)
        plt.title(f"{c1} vs {c2}")
        st.plt = plt
        return

    raise MLError(f"Invalid plot command on line {lt.line_no}.")


def _cmd_save_plot(st: MLState, lt: LineTokens) -> None:
    toks = lt.tokens
    if len(toks) != 4 or toks[:3] != ["save", "plot", "as"]:
        raise MLError(f"Invalid save plot on line {lt.line_no}.")
    if st.plt is None:
        raise MLError(f"Oops! No plot created yet (line {lt.line_no}).")
    name = _require_quoted(toks[3], what="Plot filename", line_no=lt.line_no)
    p = st.base_dir / name
    st.plt.savefig(p)
    st.last_plot_path = p
    print(f"saved plot: {p}")


def run_ml_source(source: str, *, base_dir: Path) -> None:
    np, pd, skl, keras, plt = _require_ml_deps()

    try:
        lines = lex(source)
    except LexError as e:
        raise MLError(str(e)) from e

    st = MLState(base_dir=base_dir)

    for lt in lines:
        toks = lt.tokens
        if not toks:
            continue

        # data
        if toks[:3] == ["load", "data", "from"]:
            _cmd_load_data(st, lt, pd=pd)
            continue
        if toks == ["show", "data", "info"]:
            _cmd_show_data_info(st)
            continue
        if toks == ["show", "data", "shape"]:
            _cmd_show_data_shape(st)
            continue
        if toks == ["normalize", "data"]:
            _cmd_normalize_data(st, skl=skl)
            continue
        if toks[:3] == ["split", "data", "into"]:
            _cmd_split_data(st, lt, np=np, skl=skl)
            continue

        # neural network
        if toks[:3] == ["create", "neural", "network"]:
            _cmd_create_neural_network(st, lt)
            continue
        if toks[:2] == ["add", "input"] or toks[:2] == ["add", "hidden"] or toks[:2] == ["add", "output"]:
            _cmd_add_layer(st, lt)
            continue
        if toks[:2] == ["set", "learning"] or toks[:2] == ["set", "epochs"] or toks[:2] == ["set", "batch"]:
            _cmd_set_hyperparam(st, lt)
            continue
        if toks[:2] == ["train", "model"]:
            _cmd_train_model(st, lt, np=np, skl=skl, keras=keras)
            continue
        if toks[:1] == ["show"]:
            # metrics
            if toks in (["show", "accuracy"], ["show", "loss"], ["show", "training", "progress"]):
                _cmd_show_metric(st, lt)
                continue
            if toks == ["show", "predictions"]:
                _cmd_show_predictions(st, lt, np=np)
                continue
            if toks == ["show", "model", "accuracy"]:
                _cmd_show_model_accuracy(st, lt, np=np, skl=skl)
                continue
            if toks[:2] == ["show", "matrix"]:
                _cmd_show_matrix(st, lt)
                continue
            if toks == ["show", "classifier", "accuracy"]:
                _cmd_show_classifier_accuracy(st, lt, skl=skl)
                continue

        if toks[:3] == ["save", "model", "as"]:
            _cmd_save_model(st, lt)
            continue
        if toks[:3] == ["load", "model", "from"]:
            _cmd_load_model(st, lt, keras=keras)
            continue
        if toks[:2] == ["predict", "using"] and toks[2] == "model":
            _cmd_predict_model(st, lt, np=np)
            continue

        # classic ML
        if toks[:2] in (["create", "classifier"], ["create", "regressor"]):
            _cmd_create_classifier_regressor(st, lt, skl=skl)
            continue
        if toks[:2] == ["fit", "classifier"]:
            _cmd_fit_classifier(st, lt)
            continue
        if toks[:2] == ["predict", "using"] and toks[2] == "classifier":
            _cmd_predict_classifier(st, lt)
            continue

        # matrices
        if toks[:2] == ["create", "matrix"]:
            _cmd_create_matrix(st, lt, np=np)
            continue
        if toks[:3] == ["set", "matrix", "values"]:
            _cmd_set_matrix_values(st, lt, np=np)
            continue
        if toks[:2] == ["transpose", "matrix"]:
            _cmd_transpose_matrix(st, lt, np=np)
            continue

        # plots
        if toks[:1] == ["plot"]:
            _cmd_plot(st, lt, plt=plt)
            continue
        if toks[:3] == ["save", "plot", "as"]:
            _cmd_save_plot(st, lt)
            continue

        raise MLError(f"Oops! I don't understand '{toks[0]}' on line {lt.line_no}.")
