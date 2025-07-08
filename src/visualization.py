import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def plot_sensor_data_distribution(data_path):
    df = pd.read_csv(data_path)
    features = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']
    plt.figure(figsize=(12, 8))
    for i, feature in enumerate(features, 1):
        plt.subplot(2, 2, i)
        sns.histplot(df[feature], kde=True, bins=30)
        plt.title(f'Distribution of {feature}')
    plt.tight_layout()
    plt.show()

def plot_fire_severity_counts(data_path):
    df = pd.read_csv(data_path)
    plt.figure(figsize=(6,4))
    sns.countplot(x='FireSeverity', data=df, order=df['FireSeverity'].value_counts().index)
    plt.title('Fire Severity Counts')
    plt.show()

def plot_feature_importance(model, feature_names, save_path=None):
    importances = model.feature_importances_
    plt.figure(figsize=(8, 6))
    sns.barplot(x=importances, y=feature_names, palette="viridis")
    plt.title("Feature Importance")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

def plot_roc_curve(model, X_test, y_test, label_encoder, save_path=None):
    from sklearn.metrics import roc_curve, auc
    import numpy as np
    if hasattr(model, "predict_proba"):
        y_score = model.predict_proba(X_test)
        n_classes = len(label_encoder.classes_)
        plt.figure(figsize=(8, 6))
        for i in range(n_classes):
            fpr, tpr, _ = roc_curve(y_test == i, y_score[:, i])
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, lw=2, label=f'Class {label_encoder.classes_[i]} (area = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], 'k--', lw=2)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver Operating Characteristic (ROC) Curve')
        plt.legend(loc="lower right")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    else:
        print("Model does not support probability predictions required for ROC curve.")
