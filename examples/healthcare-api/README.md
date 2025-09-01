# Healthcare API

> HIPAA-compliant healthcare management system with patient records and appointments

## Features

- Patient and provider management
- Appointment scheduling with availability
- Medical records with privacy controls
- Prescription management
- Audit logging for compliance
- FHIR R4 integration
- Secure file storage for medical documents

## Key Endpoints

```
GET    /patients           - List patients (provider access)
POST   /patients           - Register new patient
GET    /patients/{id}/records - Medical history (encrypted)
POST   /appointments       - Schedule appointment
GET    /providers/schedule - Provider availability
POST   /prescriptions      - Create prescription
GET    /audit-log         - Compliance audit trail
```

## Security & Compliance

Demonstrates row-level security, data encryption, audit trails, and healthcare-specific authorization patterns required for HIPAA compliance.

```python
# Healthcare-specific context with audit logging
class PatientsContext(Context):
    async def get_patient_records(self, patient_id: int, provider_id: int):
        # Verify provider has access to patient
        if not await self._verify_patient_provider_relationship(patient_id, provider_id):
            await self._log_unauthorized_access(patient_id, provider_id)
            raise UnauthorizedError("No access to patient records")
        
        # Log access for audit trail
        await self._log_record_access(patient_id, provider_id)
        
        return await self._get_encrypted_records(patient_id)
```