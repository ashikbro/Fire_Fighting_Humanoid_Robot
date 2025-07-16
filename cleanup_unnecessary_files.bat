@echo off
echo Cleaning up unnecessary files...

REM Remove malformed file
del "# train_fire_model.py" 2>nul

REM Remove empty __init__.py files
del app\services\__init__.py 2>nul
del app\schemas\__init__.py 2>nul
del app\models\__init__.py 2>nul
del app\db\__init__.py 2>nul
del app\core\__init__.py 2>nul
del app\api\endpoints\__init__.py 2>nul
del app\api\__init__.py 2>nul
del app\__init__.py 2>nul
del tests\__init__.py 2>nul
del vision\__init__.py 2>nul
del hardware_integration\__init__.py 2>nul

REM Remove empty test files
del tests\test_ui.py 2>nul
del tests\test_train_fire_model.py 2>nul
del tests\test_robot_controller.py 2>nul
del tests\test_predict_fire.py 2>nul
del tests\test_navigation_with_dwa.py 2>nul
del tests\test_integration.py 2>nul
del tests\test_hardware_integration.py 2>nul
del tests\test_api_simulation.py 2>nul
del tests\test_api_new.py 2>nul

REM Remove empty vision files
del vision\train_model.py 2>nul
del vision\thermal_simulation.py 2>nul
del vision\test_vision.py 2>nul
del vision\object_detector.py 2>nul
del vision\inspect_model.py 2>nul
del vision\fire_segmentation.py 2>nul

REM Remove empty script files
del scripts\retrain_model.py 2>nul
del scripts\init_database.py 2>nul
del scripts\hash_password.py 2>nul
del scripts\generate_security_keys.py 2>nul

REM Remove empty setup files
del setup_dev.sh 2>nul
del setup_dev.bat 2>nul
del run.bat 2>nul

REM Remove empty template files
del templates\login.html 2>nul
del templates\dashboard.html 2>nul

REM Remove empty config files
del requirements.txt 2>nul
del nginx\nginx.conf 2>nul
del users.txt 2>nul

REM Remove auto-generated mobile files
del mobile_app\.metadata 2>nul
del mobile_app\pubspec.lock 2>nul

echo Cleanup completed!
echo.
echo Removed unnecessary empty files and placeholders.
echo You may need to implement actual functionality for the core modules.
pause
