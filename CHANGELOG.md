# Changelog

All notable changes to this project will be documented in this file.

## [0.6.0] - 2025-01-30

### Added

- Building Classification 2018 (Rakennusluokka_2018)
  - Classification codes and mappings
  - Building classes integration into reporting system
  - Property type filtering with explanatory notes
- Comprehensive debug functions
- Linux shell script equivalent of `startdev.ps1`
- `lukittu` field to kohde table to indicate if the kohde is locked

### Changed

- Enhanced property type handling:
  - Improved property formation logic and validation
  - Enhanced type definition algorithms
  - Enhanced address number matching
  - Improved basic fee registry data processing
- Upgraded code documentation for better maintainability
- Fixed PostgreSQL 16 compatibility issues with DevDB public schema privileges

### Documentation

- Updated README.md with new features and configurations
- Added comprehensive code documentation
- Improved debug message clarity

## [0.6.1] - 2025-02-13

### Added

- Rakennusluokka_2018 integration:
  - Added to rakennukset view with selite
  - Enhanced building classification support
- QGIS project improvements:
  - New separate layers for kohdetyypit
  - Migration system for QGIS projects
  - Documentation for QGIS project migrations
- Lopetusilmoitus handling enhancements
- Enhanced logging and debugging capabilities
- Null date option in velvoite reports
- Type checking mode (basic) for Python analysis

### Fixed

- Kohdetyyppi determination logic:
  - Improved rakennusluokka_2018 checks
  - Enhanced building type validation
- Query optimizations:
  - Added proper parentheses in kohde filtering
  - Improved velvoite ordering with DESC, id DESC
  - Enhanced date range handling
- Kompostitietojen processing and validation
- Building data processing improvements:
  - Enhanced DVV building data handling
  - Improved building cluster logic
  - Better ownership and resident matching

### Changed

- Enhanced documentation:
  - Added QGIS project migration guide
  - Updated README.md with new configurations
- Improved data validation in velvoite system
- Optimized building data processing:
  - Added PRT tracking
  - Enhanced logging for building processing
  - Improved transaction handling

## [0.6.2] - 2025-02-17

### Fixed

- Velvoite processing repaired:
  - Fixed velvoite processing
  - Fixed Kohteiden luppupvm handling
