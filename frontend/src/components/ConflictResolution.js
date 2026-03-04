import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { Warning } from '@mui/icons-material';

const ConflictResolution = ({ open, conflict, onResolve, onCancel, currentData, serverData }) => {
  if (!conflict) return null;

  const handleUseServer = () => {
    onResolve('server', serverData);
  };

  const handleUseLocal = () => {
    onResolve('local', currentData);
  };

  const handleMerge = () => {
    // Merge logic would go here
    onResolve('merge', { ...serverData, ...currentData });
  };

  return (
    <Dialog open={open} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Warning color="warning" />
          <Typography variant="h6">Edit Conflict Detected</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          This record was modified by another user while you were editing. Please choose how to resolve the conflict.
        </Alert>

        <Typography variant="body1" gutterBottom>
          <strong>Current Version:</strong> {conflict.current_version}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Your changes will be lost if you choose to use the server version. You can also manually merge the changes.
        </Typography>

        {serverData && (
          <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Server Version:
            </Typography>
            <Typography variant="body2" component="pre" sx={{ fontSize: '0.875rem' }}>
              {JSON.stringify(serverData, null, 2)}
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} color="secondary">
          Cancel
        </Button>
        <Button onClick={handleUseLocal} color="primary" variant="outlined">
          Keep My Changes
        </Button>
        <Button onClick={handleUseServer} color="primary" variant="outlined">
          Use Server Version
        </Button>
        <Button onClick={handleMerge} color="primary" variant="contained">
          Merge Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConflictResolution;
