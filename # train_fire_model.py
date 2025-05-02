# train_fire_model.py

jls_extract_var = pandas
import jls_extract_var as pd

from sklearn.model_selection import train_test_split

from sklearn.ensemble import RandomForestClassifier

from sklearn.preprocessing import LabelEncoder

from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

import joblib


# Load dataset
# Load dataset

# Load dataset

# Load dataset



df = pd.read_csv("fire_data_bangladesh.csv")


# Features and target

X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]

y = df['FireSeverity']


# Encode labels

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)


# Split data

X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)


# Train model

model = RandomForestClassifier(n_estimators=100, random_state=42)

model.fit(X_train, y_train)


# Predict

y_pred = model.predict(X_test)


# Evaluation

print("Classification Report:\n", classification_report(y_test, y_pred, target_names=label_encoder.classes_))


# Confusion Matrix

conf_matrix = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(6, 4))

sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='OrRd',

            xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)

plt.title("Confusion Matrix")

plt.xlabel("Predicted")

plt.ylabel("Actual")

plt.savefig("confusion_matrix.png")
plt.close()


# Save model and encoder

joblib.dump(model, "fire_severity_model.pkl")

joblib.dump(label_encoder, "label_encoder.pkl")


print("✅ Model and encoder saved!")

print("📊 Confusion matrix saved as confusion_matrix.png")


    
