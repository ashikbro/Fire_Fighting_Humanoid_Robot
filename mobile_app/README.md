# Fire Fighting Humanoid Robot Mobile Controller

A comprehensive Flutter mobile application for controlling and monitoring a fire-fighting humanoid robot. This app provides real-time robot control, sensor monitoring, camera feeds, and emergency response capabilities.

## Features

### 🎮 Robot Control
- **Movement Controls**: Forward, backward, left, right with intuitive joystick-style interface
- **Water Cannon Control**: On/off controls for fire suppression system
- **Emergency Stop**: Large, prominent emergency stop button with visual feedback
- **Speed Dial Actions**: Quick access to common functions

### 📊 Sensor Monitoring
- **Fire Detection**: Temperature, smoke level, gas detection, and flame sensors
- **Environmental Monitoring**: Humidity and distance sensors
- **System Status**: Battery voltage and motor temperature monitoring
- **Real-time Alerts**: Visual and audio alerts for emergency conditions

### 📹 Camera System
- **Live Video Feed**: Real-time camera feed from robot
- **Recording Capability**: Start/stop video recording
- **Night Vision**: Toggle between normal and night vision modes
- **Zoom Control**: Digital zoom with slider control
- **Image Capture**: Take snapshots during operation

### ⚙️ Settings & Configuration
- **Connection Settings**: Configure robot IP address and port
- **App Preferences**: Dark mode, notifications, auto-connect
- **Emergency Contacts**: Configure emergency response contacts
- **System Reset**: Reset all settings to defaults

### 🎨 UI/UX Features
- **Modern Design**: Material Design 3 with custom fire-fighting theme
- **Responsive Layout**: Works on phones and tablets
- **Dark/Light Theme**: Automatic theme switching based on system preferences
- **Animations**: Smooth transitions and visual feedback
- **Accessibility**: Screen reader support and high contrast options

## Getting Started

### Prerequisites
- Flutter SDK (>=3.1.5)
- Dart SDK
- Android Studio / VS Code
- Physical device or emulator

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mobile_app
```

2. Install dependencies:
```bash
flutter pub get
```

3. Run the app:
```bash
flutter run
```

### Building for Release

#### Android
```bash
flutter build apk --release
```

#### iOS
```bash
flutter build ios --release
```

#### Windows
```bash
flutter build windows --release
```

#### macOS
```bash
flutter build macos --release
```

#### Linux
```bash
flutter build linux --release
```

## Dependencies

### Core Dependencies
- `flutter`: Flutter SDK
- `cupertino_icons`: iOS-style icons
- `http`: HTTP client for API communication
- `shared_preferences`: Local data storage

### UI/UX Libraries
- `flutter_speed_dial`: Floating action button with multiple actions
- `animations`: Enhanced animations and transitions

### Camera & Media
- `camera`: Camera access and control
- `image`: Image processing utilities

### Communication
- `web_socket_channel`: Real-time WebSocket communication

### Storage
- `sqflite`: Local SQLite database
- `path`: File path utilities

### Permissions
- `permission_handler`: Runtime permissions management

## Architecture

### Project Structure
```
lib/
├── main.dart                 # App entry point
├── themes/
│   └── app_theme.dart       # App theming and colors
├── screens/
│   ├── splash_screen.dart   # Loading screen
│   ├── home_screen.dart     # Main dashboard
│   ├── camera_screen.dart   # Camera controls
│   ├── sensor_monitoring_screen.dart  # Sensor data
│   └── settings_screen.dart # App settings
└── widgets/
    ├── status_card.dart     # Status display cards
    ├── robot_controls.dart  # Movement controls
    ├── emergency_button.dart # Emergency stop
    └── sensor_card.dart     # Sensor data cards
```

### Key Components

#### Themes (`themes/app_theme.dart`)
- Defines color scheme for fire-fighting theme
- Supports both light and dark modes
- Consistent styling across the app

#### Screens
- **SplashScreen**: Animated loading screen with app branding
- **HomeScreen**: Main dashboard with robot status and quick controls
- **CameraScreen**: Live video feed with recording and zoom controls
- **SensorMonitoringScreen**: Real-time sensor data and alerts
- **SettingsScreen**: App configuration and preferences

#### Widgets
- **StatusCard**: Reusable status display component
- **RobotControls**: Movement control interface
- **EmergencyButton**: Prominent emergency stop with animation
- **SensorCard**: Individual sensor data display

## Communication Protocol

The app communicates with the robot using:
- **HTTP REST API**: For configuration and status updates
- **WebSockets**: For real-time control commands and sensor data
- **RTSP/WebRTC**: For video streaming (when implemented)

### API Endpoints (Planned)
- `GET /status` - Robot status and sensor data
- `POST /control/movement` - Movement commands
- `POST /control/water` - Water cannon control
- `POST /emergency/stop` - Emergency stop
- `GET /camera/stream` - Video stream endpoint

## Safety Features

### Emergency Systems
- **Emergency Stop**: Immediately halts all robot operations
- **Connection Monitoring**: Automatic alerts for connection loss
- **Battery Monitoring**: Low battery warnings and alerts
- **Sensor Alerts**: Visual and audio alerts for dangerous conditions

### Data Validation
- Input validation for all control commands
- Connection timeout handling
- Error recovery mechanisms

## Customization

### Themes
Modify `themes/app_theme.dart` to customize:
- Primary and secondary colors
- Button styles and shapes
- Card designs and shadows

### Controls
Update `widgets/robot_controls.dart` to:
- Add new movement commands
- Modify control layout
- Integrate with different robot APIs

### Sensors
Extend `screens/sensor_monitoring_screen.dart` to:
- Add new sensor types
- Customize alert thresholds
- Integrate additional monitoring systems

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki

## Version History

### v1.0.0 (Current)
- Initial release
- Basic robot control functionality
- Sensor monitoring system
- Camera interface
- Settings management
- Emergency safety features

### Planned Features
- [ ] Real robot integration
- [ ] Video recording to local storage
- [ ] Multi-robot support
- [ ] Advanced path planning interface
- [ ] Voice commands
- [ ] Gesture controls
- [ ] Augmented reality overlay
- [ ] Cloud data synchronization
