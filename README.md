# AgriYield MLOps

### Agricultural Yield Prediction & ML Lifecycle Monitoring

AgriYield MLOps is a collaborative machine learning engineering project developed by **Oumayma Ihrissane and Douae Laayouni**. It focuses on agricultural crop yield prediction and the development of an end-to-end MLOps platform for monitoring and managing the lifecycle of machine learning models.

The project combines **predictive modeling, data processing, model versioning, a web application, and MLOps practices**, with particular emphasis on data drift detection, predictive performance monitoring, and model retraining.

The objective is to move beyond a standalone machine learning notebook toward a reproducible, observable, and maintainable ML system.

---

## 1. Project Objectives

The main objectives of AgriYield MLOps are:

- **Crop Yield Prediction:** Develop a regression model to estimate agricultural yields based on input characteristics.
- **Data Drift Detection:** Identify statistical changes between reference training data and incoming observations.
- **Performance Monitoring:** Evaluate model performance over time using actual crop yields and regression metrics.
- **Monitoring and Alerts:** Track monitoring results, identify potential reliability issues, and support alert management.
- **Model Versioning:** Manage datasets, models, and pipeline configurations using Git and DVC.
- **Model Retraining:** Support the evaluation and comparison of candidate model versions before deployment.

## 2. Technology Stack

| Component | Technologies |
|---|---|
| Programming Language | Python |
| Machine Learning | Scikit-learn, Pandas, NumPy |
| Model Evaluation | MAE, RMSE, R² |
| Data Drift Monitoring | Evidently AI (planned integration) |
| Backend API | FastAPI, Pydantic |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Database | MariaDB (target integration) |
| Data & Model Versioning | Git, GitHub, DVC |
| Development Environment | VS Code, Jupyter Notebook |
| Automation | GitHub Actions (planned) |

## 3. System Architecture

The target architecture integrates agricultural yield prediction, data storage, statistical monitoring, alerts, and model lifecycle management.

```text
                 AgriYield Web Application
                     HTML / CSS / JS
                            |
                            v
                        FastAPI
                            |
                +-----------+-----------+
                |                       |
                v                       v
          ML Prediction             Database
           Model V1              Observations
                |                & Predictions
                |                       |
                +-----------+-----------+
                            |
                            v
                       Evidently AI
                      Monitoring Layer
                            |
                  +---------+---------+
                  |                   |
                  v                   v
              Data Drift         Performance
               Analysis           Monitoring
                  |                   |
                  +---------+---------+
                            |
                            v
                     Alerts & Reports
                            |
                            v
                   Retraining Decision
                            |
                            v
                   Model V1 / V2 Review

                    Git + DVC Versioning
```

*This architecture represents the intended system. Some monitoring, persistence, and retraining components are still under development.*

## 4. Main Features

### 4.1. Agricultural Yield Prediction

The prediction module is designed to estimate crop yields from agricultural characteristics.

The machine learning pipeline includes:

- Data cleaning and preprocessing.
- Training, validation, and test data preparation.
- Regression model training and evaluation.
- Model serialization and versioning.
- Prediction services for new agricultural observations.

The initial trained model is referred to as **Model V1**.

### 4.2. Data Drift Detection

The monitoring system is designed to integrate Evidently AI to detect distribution changes between reference training data and incoming production observations.

The planned workflow consists of:

1. Selecting a model and reference dataset.
2. Selecting incoming observations or an analysis period.
3. Comparing current data distributions against the reference baseline.
4. Identifying features affected by significant distribution changes.
5. Recording monitoring results for future analysis.

Data drift does not necessarily imply model performance degradation, but it can indicate the need for further investigation.

### 4.3. Model Performance Monitoring

Model performance monitoring evaluates how accurately the deployed model predicts agricultural yields when actual values become available.

The main regression metrics are:

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| R² | Coefficient of Determination |

The monitoring system is intended to compare current performance against the initial evaluation baseline.

Performance degradation can only be assessed when sufficient ground-truth observations are available.

### 4.4. Monitoring Dashboard

The planned monitoring interface is organized into five main sections:

| Section | Description |
|---|---|
| Data Drift | Execute and inspect statistical drift analyses |
| Performance | Monitor predictive quality using regression metrics |
| Dashboard | Visualize monitoring indicators and recent analyses |
| History | Access previously executed monitoring analyses |
| Alerts | Track detected anomalies and their resolution status |

The dashboard is designed to display previously recorded results without automatically rerunning monitoring analyses.

### 4.5. Prediction History

The application is designed to maintain an observation and prediction history.

This functionality aims to provide traceability through:

- Recording incoming agricultural observations.
- Storing predicted crop yields.
- Consulting previous prediction results.
- Filtering historical observations.
- Associating actual yields with previous predictions when available.

The stored observations will also serve as inputs for subsequent drift and performance monitoring.

### 4.6. Model Retraining and Lifecycle Management

The planned model lifecycle workflow supports the evaluation of candidate model versions when monitoring results indicate a potential need for retraining.

The proposed process includes:

1. Detecting significant data drift or performance degradation.
2. Reviewing monitoring results and retraining conditions.
3. Training a candidate model version.
4. Evaluating and comparing the candidate against the current model.
5. Approving deployment only when validation criteria are satisfied.
6. Supporting rollback when necessary.

A new model is not intended to replace the existing one automatically based solely on a drift alert.

## 5. Project Structure

```text
AgriYield_Mlops/
├── api/                 # FastAPI application and schemas
├── backend/             # Backend package
├── frontend/            # Web interface and static assets
├── src/                 # ML pipeline and application services
├── notebooks/           # Model development and experiments
├── data/                # DVC-managed datasets
├── models/              # DVC-managed model artifacts
├── references/          # Baseline datasets, metrics and statistics
├── reports/             # Exploratory and evaluation reports
├── CSVtest/             # Input validation samples
├── exports/             # Sample exported observations
├── tests/               # Testing directory
├── .github/             # GitHub configuration
├── .dvc/                # DVC configuration
├── data.dvc             # Dataset tracking metadata
├── models.dvc           # Model tracking metadata
├── dvc.yaml             # DVC pipeline definition
├── params.yaml          # ML pipeline parameters
├── requirements.txt     # Python dependencies
└── README.md
```

## 6. Reference Baseline (T0)

AgriYield MLOps uses an initial reference state, called **T0**, as the baseline for monitoring future observations and model performance.

Two types of references are distinguished.

**Data Baseline**

The data baseline represents the statistical characteristics of the reference training dataset, including feature distributions and descriptive statistics.

It is used to detect changes in incoming data distributions.

**Performance Baseline**

The performance baseline represents the initial evaluation results of Model V1 on an independent test dataset.

It provides a reference for assessing changes in predictive performance.

These baselines serve different monitoring purposes and are evaluated separately.

## 7. Data and Model Versioning

The project uses Git and DVC to support reproducibility and traceability.

| Tool | Responsibility |
|---|---|
| Git | Source code and configuration versioning |
| GitHub | Repository hosting and collaboration |
| DVC | Dataset and model artifact tracking |
| DVC Remote Storage | Storage of versioned data and model files |

The DVC configuration currently references a local storage location. Access to the corresponding datasets and models from another machine therefore requires an appropriately configured, accessible DVC remote.

A dedicated model registry is not included in the current architecture.

## 8. Monitoring Validation Scenarios

Three scenarios have been defined to evaluate the intended monitoring capabilities.

| Scenario | Description | Expected Behavior |
|---|---|---|
| T1 — Stable Data | Incoming observations follow the reference distributions | No significant drift detected |
| T2 — Data Drift | Selected agricultural features undergo controlled distribution changes | Drift detected and reported |
| T3 — Performance Degradation | Prediction errors increase relative to the reference baseline | Performance degradation identified |

These scenarios are intended for the end-to-end validation of the monitoring system.

## 9. Development Status

AgriYield MLOps is currently under active development.

### Available Foundations

- Agricultural data preparation and preprocessing scripts.
- Initial machine learning model development pipeline.
- Model evaluation reports and baseline reference artifacts.
- FastAPI application and prediction service source code.
- Frontend templates, styles, and JavaScript components.
- Git and DVC configuration for version control.

### Integration and Validation in Progress

- End-to-end prediction API and database integration.
- Evidently AI data drift and performance monitoring.
- Monitoring dashboard and analysis history.
- Persistent alert generation and management.
- Model retraining and candidate version comparison.
- Automated MLOps workflows.
- End-to-end validation and testing.

The availability of source code does not necessarily indicate that all application components are fully integrated or operational.

## 10. Local Development

### Clone the Repository

```bash
git clone https://github.com/oumaymaih/AgriYield_Mlops.git
cd AgriYield_Mlops
```

### Create a Virtual Environment

```bash
python -m venv .venv
```

### Activate the Environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Configuration

Use `.env.example` as a template to configure the database connection and other environment-specific settings.

### DVC Artifacts

Datasets and model artifacts are tracked using DVC.

The repository includes the corresponding metadata, but downloading the actual artifacts requires access to a configured DVC remote.

Complete application startup instructions will be documented as the backend, database, and monitoring integrations are validated.

## 11. Roadmap

- [x] Define the agricultural ML use case.
- [x] Establish the ML pipeline structure.
- [x] Prepare model reference artifacts and evaluation reports.
- [x] Introduce Git and DVC tracking.
- [x] Add backend API and frontend source components.
- [ ] Validate the complete prediction workflow.
- [ ] Complete database integration.
- [ ] Integrate Evidently AI for data drift monitoring.
- [ ] Implement model performance monitoring.
- [ ] Complete monitoring dashboards, history, and alerts.
- [ ] Implement candidate retraining and model comparison.
- [ ] Execute stable-data, data-drift, and performance-drift scenarios.
- [ ] Validate and document the end-to-end application.

## 12. Contributors

This project is collaboratively developed with:

**Douae Laayouni**

AgriYield MLOps is a collaborative academic project focused on applying machine learning engineering and MLOps practices to agricultural yield prediction, statistical monitoring, and model lifecycle management.

## 13. Project Vision

AgriYield MLOps aims to demonstrate how machine learning can evolve from a standalone predictive model into a monitored and maintainable application.

By combining agricultural yield prediction with data drift detection, performance monitoring, version control, and model lifecycle management, the project explores practical approaches to developing reliable machine learning systems.

---

**Project Status:** Work in Progress  
**Last Updated:** November 2026
