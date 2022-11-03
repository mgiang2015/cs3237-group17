import { StatusBar } from 'expo-status-bar';
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Alert,
} from 'react-native';
import { Input, Button} from '@rneui/base';
import AsyncStorage from '@react-native-async-storage/async-storage';
import init from 'react_native_mqtt';

init({
  size: 10000,
  storageBackend: AsyncStorage,
  defaultExpires: 1000 * 3600 * 24,
  enableCache: true,
  sync : {}
});
const options = {
  host: 'broker.emqx.io',
  port: 8083,
  path: '/testTopic',
  id: 'id_' + parseInt(Math.random()*100000)
};
client = new Paho.MQTT.Client(options.host, options.port, options.path);


export default function App() {
  const [topic, setTopic] = useState('')
  const [subscribedTopic, setSubscribedTopic] = useState('')
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('')

  const onConnect = () => {
    console.log('onConnect');
    setStatus('connected')

    // subscribe to topic automatically
    subscribeTopic("HELLOWORLD")
  }

  const onFailure = (err) => {
    console.log('Connect failed!');
    console.log(err);
    setStatus('failed');
  }

  const connect = () => {
    setStatus('isFetching')
    client.connect({
      onSuccess: onConnect,
      useSSL: false,
      timeout: 3,
      onFailure: onFailure
    });
  }

  const disconnect = () => {
    client.disconnect()
    setStatus('')
    setSubscribedTopic('')
    console.log("disconnected")
  }

  const onConnectionLost= (responseObject) =>{
    if (responseObject.errorCode !== 0) {
      console.log('onConnectionLost:' + responseObject.errorMessage);
    }
  }

  const onMessageArrived = (message)=> {
    console.log('onMessageArrived:' + message.payloadString);
    Alert.alert(
      "Message received",
      message.payloadString,
      [
        {
          text: "Noted!"
        }
      ]
    )
  }

  const subscribeTopic = (topicName) => {
    setSubscribedTopic(topicName)
    client.subscribe(topicName, { qos: 0 });
  }

  const sendMessage = () => {
    var mqttMessage = new Paho.MQTT.Message(options.id + ':' + message);
    mqttMessage.destinationName = subscribedTopic;
    client.send(mqttMessage);
  }

  // set up client
  useEffect(() => {
    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
  }, [client])

  return (
    <View style={styles.container}>
      <Text>Open up App.js to start working on your app!</Text>
      <StatusBar style="auto" />
      {
        status === 'connected' 
        ? 
        <Button
          type='solid'
          title='DISCONNECT'
          onPress={disconnect}
          buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
          icon={{ name: 'lan-disconnect', type: 'material-community', color: 'white' }}
        />
        : 
        <Button
          type='solid'
          title='CONNECT'
          onPress={connect}
          buttonStyle={{
            marginBottom:50,
            backgroundColor: status === 'failed' ? 'red' : '#397af8'
          }}
          icon={{ name: 'lan-connect', type: 'material-community', color: 'white' }}
          loading={status === 'isFetching' ? true : false}
          disabled={status === 'isFetching' ? true : false}
        />
      }
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
});