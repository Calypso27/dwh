# Benchmark ML initial

Decoupage chronologique : 120,000 train, 30,000 test.

| Tache | Modele | Metriques |
|---|---|---|
| engagement | dummy | mae=1.9190; rmse=2.5453; r2=-0.1208 |
| engagement | ridge | mae=1.8359; rmse=2.2441; r2=0.1288 |
| engagement | random_forest | mae=1.1502; rmse=1.5350; r2=0.5924 |
| virality | dummy | f1_viral=0.0000; balanced_accuracy=0.5000; precision_viral=0.0000; recall_viral=0.0000; pr_auc=0.1027 |
| virality | logistic_regression | f1_viral=0.3751; balanced_accuracy=0.7399; precision_viral=0.2531; recall_viral=0.7244; pr_auc=0.4611 |
| virality | random_forest | f1_viral=0.5327; balanced_accuracy=0.8156; precision_viral=0.4117; recall_viral=0.7545; pr_auc=0.5437 |
