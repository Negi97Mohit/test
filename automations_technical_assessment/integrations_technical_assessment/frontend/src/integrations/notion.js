import { useState, useEffect } from 'react';
import {
    Box,
    Button,
    CircularProgress,
} from '@mui/material';
import axios from 'axios';

export const NotionIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [notionItems, setNotionItems] = useState([]);

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/notion/authorize`, formData);
            const authURL = response?.data;

            const newWindow = window.open(authURL, 'Notion Authorization', 'width=600, height=600');
            const pollTimer = window.setInterval(() => {
                if (newWindow?.closed !== false) { 
                    window.clearInterval(pollTimer);
                    handleWindowClosed();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail);
        }
    };

    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/notion/credentials`, formData);
            const credentials = response.data; 
            console.log(credentials); // Add this line to inspect the credentials object
            if (credentials) {
                setIsConnected(true);
                setIntegrationParams(prev => ({ ...prev, credentials: credentials, type: 'Notion' }));
                fetchNotionItems(credentials);
            }
            setIsConnecting(false);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail);
        }
    };

    const fetchNotionItems = async (credentials) => {
        try {
          const response = await fetch('http://localhost:8000/integrations/notion/load', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ access_token: credentials.access_token }),
          });
      
          if (response.ok) {
            const data = await response.json();
            console.log('Notion items:', data);
            // Update your state with the fetched data
          } else {
            throw new Error('Failed to fetch items');
          }
        } catch (error) {
          console.error('Error fetching items:', error);
        }
      };
      
    useEffect(() => {
        if (integrationParams?.credentials) {
            setIsConnected(true);
            fetchNotionItems(integrationParams.credentials);
        }
    }, [integrationParams]);

    return (
        <Box sx={{ mt: 2 }}>
            <Box display='flex' alignItems='center' justifyContent='center' sx={{ mt: 2 }}>
                {isConnected ? (
                    <Button
                        variant='contained'
                        color='error'
                        onClick={() => {
                            setIsConnected(false);
                            setIntegrationParams({});
                        }}
                    >
                        Disconnect from Notion
                    </Button>
                ) : (
                    <Button
                        variant='contained'
                        color='primary'
                        onClick={handleConnectClick}
                        disabled={isConnecting}
                    >
                        {isConnecting ? <CircularProgress size={20} /> : 'Connect to Notion'}
                    </Button>
                )}
            </Box>
            {notionItems.length > 0 && (
                <Box sx={{ mt: 2 }}>
                    <h3>Notion Items:</h3>
                    <ul>
                        {notionItems.map(item => (
                            <li key={item.id}>{item.name}</li>
                        ))}
                    </ul>
                </Box>
            )}
        </Box>
    );
};
