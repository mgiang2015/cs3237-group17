import { createContext, useState, useEffect, useContext } from 'react';
import mqtt from 'mqtt';
import { StyleSheet, Text, View } from 'react-native';

const HOST = 'broker.emqx.io'
const PORT = 1883
const WS_PORT = 8083 // websocket port
const HOST_URL = `ws://${HOST}:${WS_PORT}/mqtt`
const ID = 'uname'

// idk what this is lmao
export const QosOption = createContext([])
const qosOption = [
  {
    label: '0',
    value: 0,
  }, {
    label: '1',
    value: 1,
  }, {
    label: '2',
    value: 2,
  },
];

const connectOptions = {
  clientId: ID,
  username: 'hello',
  password: '123kek',
  keepalive: 30,
  protocolId: 'MQTT',
  protocolVersion: 4,
  clean: true,
  reconnectPeriod: 1000,
  connectTimeout: 30 * 1000,
  will: {
    topic: 'WillMsg',
    payload: 'Connection Closed abnormally..!',
    qos: 0,
    retain: false
  },
  rejectUnauthorized: false
};

export default function MqttLog() {
  const [client, setClient] = useState(null);
  const [connectStatus, setConnectStatus] = useState('Connect');
  const [isSubed, setIsSub] = useState(false);
  const [payload, setPayload] = useState({});

  // client api
  const mqttConnect = (mqttOption) => {
    setConnectStatus('Connecting');
    setClient(mqtt.connect(HOST, mqttOption));
  };

  const mqttDisconnect = () => {
    if (client) {
      client.end(() => {
        setConnectStatus('Connect');
      });
    }
  }

  const mqttPublish = (context) => {
    if (client) {
      const { topic, qos, payload } = context;
      client.publish(topic, payload, { qos }, error => {
        if (error) {
          console.log('Publish error: ', error);
        }
      });
    }
  }

  const mqttSub = (subscription) => {
    if (client) {
      const { topic, qos } = subscription;
      client.subscribe(topic, { qos }, (error) => {
        if (error) {
          console.log('Subscribe to topics error', error)
          return
        }
        setIsSub(true)
      });
    }
  };

  const mqttUnSub = (subscription) => {
    if (client) {
      const { topic } = subscription;
      client.unsubscribe(topic, error => {
        if (error) {
          console.log('Unsubscribe error', error)
          return
        }
        setIsSub(false);
      });
    }
  };

  // Set up client
  useEffect(() => {
    if (client) {
      client.on('connect', () => {
        setConnectStatus('Connected');
      });
      client.on('error', (err) => {
        console.error('Connection error: ', err);
        client.end();
      });
      client.on('reconnect', () => {
        setConnectStatus('Reconnecting');
      });
      client.on('message', (topic, message) => {
        const payload = { topic, message: message.toString() };
        setPayload(payload);
      });

      // connect client
      mqttConnect(connectOptions);
      mqttSub({ topic: "WORLD", qos: useContext(QosOption) })
    }
  }, [client])

  return (
    <View>
      <Text>{"Check log for details!"}</Text>
    </View>
  )
}