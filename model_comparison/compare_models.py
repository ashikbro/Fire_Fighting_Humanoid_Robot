import matplotlib.pyplot as plt
import numpy as np

from sklearn.metrics import precision_recall_curve, average_precision_score
import joblib
import numpy as np
import matplotlib.pyplot as plt

def plot_precision_recall_curve(model_path='models/fire_severity_model.pkl', data_path='data/fire_data_bangladesh.csv'):
    # Load model and data
    model = joblib.load(model_path)
    import pandas as pd
    df = pd.read_csv(data_path)
    X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]
    y = df['FireSeverity']

    # Encode labels
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Predict probabilities
    y_scores = model.predict_proba(X)

    # For multi-class, plot precision-recall for each class
    plt.figure()
    for i, class_label in enumerate(le.classes_):
        precision, recall, _ = precision_recall_curve(y_encoded == i, y_scores[:, i])
        ap = average_precision_score(y_encoded == i, y_scores[:, i])
        plt.plot(recall, precision, label=f'{class_label} (AP={ap:.2f})')

    plt.title('Precision-Recall Curve')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    plt.grid(True)
    plt.savefig('model_comparison/precision_recall.png')
    plt.close()

def plot_confusion_matrix(model_path='models/fire_severity_model.pkl', data_path='data/fire_data_bangladesh.csv'):
    import pandas as pd
    from sklearn.metrics import confusion_matrix
    from sklearn.preprocessing import LabelEncoder

    # Load model and data
    model = joblib.load(model_path)
    df = pd.read_csv(data_path)
    X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]
    y = df['FireSeverity']

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Predict
    y_pred = model.predict(X)

    # Compute confusion matrix
    cm = confusion_matrix(y_encoded, y_pred)
    classes = le.classes_

    fig, ax = plt.subplots()
    cax = ax.matshow(cm, cmap='Blues')
    plt.title('Confusion Matrix')
    fig.colorbar(cax)
    ax.set_xticks(np.arange(len(classes)))
    ax.set_yticks(np.arange(len(classes)))
    ax.set_xticklabels(classes)
    ax.set_yticklabels(classes)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')

    for (i, j), val in np.ndenumerate(cm):
        ax.text(j, i, val, ha='center', va='center')

    plt.savefig('model_comparison/confusion_matrix.png')
    plt.close()

if __name__ == "__main__":
    plot_precision_recall_curve()
    plot_confusion_matrix()
