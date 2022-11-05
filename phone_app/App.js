import { setStatusBarBackgroundColor, StatusBar } from 'expo-status-bar';
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


const CONNECTED = 'CONNECTED'
const DISCONNECTED = 'DISCONNECTED'
const FETCHING = 'FETCHING'
const ADDING_DEVICE = 'ADDING_DEVICE'
const PHONE_CHANNEL = "group17/tvManager/phone"
const CONNECT_DEVICE_CHANNEL = "group17/tvManager/connectDevice"
const CONNECT_DEVICE_MESSAGE = "CONNECT_DEVICE"
const CONNECT_DEVICE_DONE = "DONE"
const TV_STATE_ON = "ON"
const TV_STATE_OFF = "OFF"
const MESSAGE_TV_OFF = "TV_OFF"
const MESSAGE_TV_ON = "TV_ON"
const JSON_MESSAGE_KEY = "msg"

export default function App() {
  const [status, setStatus] = useState(DISCONNECTED)
  const [tvState, setTvState] = useState(TV_STATE_ON)
  const [offTime, setOffTime] = useState(new Date())

  const onConnect = () => {
    console.log('onConnect');
    setStatus(CONNECTED)

    // subscribe to topic automatically
    subscribeTopic("HELLOWORLD")

    // subscribe to our actual endpoint
    subscribeTopic(PHONE_CHANNEL)
  }

  const onFailure = (err) => {
    console.log('Connect failed!');
    console.log(err);
    setStatus(DISCONNECTED);
  }

  const connect = () => {
    setStatus(FETCHING)
    client.connect({
      onSuccess: onConnect,
      useSSL: false,
      timeout: 3,
      onFailure: onFailure
    });
  }

  const disconnect = () => {
    client.disconnect()
    setStatus(DISCONNECTED)
    console.log("disconnected")
  }

  const onConnectionLost= (responseObject) =>{
    if (responseObject.errorCode !== 0) {
      console.log('onConnectionLost:' + responseObject.errorMessage);
    }
  }

  const onMessageArrived = (message)=> {
    console.log('onMessageArrived:' + message.payloadString);

    // logic to handle different messages
    // handle DONE to /connectDevice
    const jsonMessage = JSON.parse(message.payloadString)
    console.log(jsonMessage)
    if (jsonMessage[JSON_MESSAGE_KEY] === CONNECT_DEVICE_DONE) {
      console.log("DONE detected")
      setStatus(CONNECTED)
      unsubscribeTopic(CONNECT_DEVICE_CHANNEL)
    }

    // handle TV_OFF to /phone
    if (jsonMessage[JSON_MESSAGE_KEY] === MESSAGE_TV_OFF) {
      console.log("TV has turned off")
      setTvState(TV_STATE_OFF)
      setOffTime(new Date())
    }

    // handle TV_ON to /phone
    if (jsonMessage[JSON_MESSAGE_KEY] === MESSAGE_TV_ON) {
      console.log("TV has turned on")
      setTvState(TV_STATE_ON)
    }
  }

  const subscribeTopic = (topicName) => {
    client.subscribe(topicName, { qos: 0 });
  }

  const unsubscribeTopic = (topicName) => {
    client.unsubscribe(topicName);
  }

  const sendMessage = (message, topic) => {
    var mqttMessage = new Paho.MQTT.Message(`{"msg":"${message}"}`);
    mqttMessage.destinationName = topic;
    client.send(mqttMessage);
  }

  // startConnectDevice
  const startConnectDevice = () => {
    // set state to fetching first to get that loading sign
    setStatus(ADDING_DEVICE)
    console.log("Set status to ADDING DEVICE")

    // subscribe to new shit
    subscribeTopic(CONNECT_DEVICE_CHANNEL)
    console.log("SUBSCRIBED TO NEW SHIT")

    // send message to set up channel
    sendMessage(CONNECT_DEVICE_MESSAGE, CONNECT_DEVICE_CHANNEL)
    console.log("SENT MESSAGE")
  }

  // set up client
  useEffect(() => {
    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
  }, [client])

  // Button renderer
  const renderView = () => {
    // connected and TV is on
    if (status === CONNECTED) {
      return (
        <View>
          {
            tvState === TV_STATE_ON 
            ?
            <Text>
              {"TV is currently on!"}
            </Text>
            :
            <Text>
              {`TV has been off since ${offTime.getHours()}:${offTime.getMinutes()}:${offTime.getSeconds()}`}
            </Text>
          }
          <Button
            type='solid'
            title='DISCONNECT'
            onPress={disconnect}
            buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
            icon={{ name: 'lan-disconnect', type: 'material-community', color: 'white' }}
          />
          <Button 
            type='solid'
            title='SET UP NEW DEVICE'
            onPress={startConnectDevice}
          />
        </View>
      )
    }

    if (status === ADDING_DEVICE) {
      return (
        <View>
          <Text>{"Please wait. We are gathering info about your new device"}</Text>
          <Button
              type='solid'
              title='STOP SET UP'
              onPress={() => setStatus(CONNECTED)}
              buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
            />
        </View>
      )
    }

    if (status !== CONNECTED) {
      return (
        <Button
          type='solid'
          title='CONNECT'
          onPress={connect}
          buttonStyle={{
            marginBottom:50,
            backgroundColor: status === 'failed' ? 'red' : '#397af8'
          }}
          icon={{ name: 'lan-connect', type: 'material-community', color: 'white' }}
          loading={status === FETCHING ? true : false}
          disabled={status === FETCHING ? true : false}
        />
      )
    }
  }

  return (
    <View style={styles.container}>
      <Text>{status === CONNECTED ? "Press DISCONNECT to turn off the application" : "Press CONNECT to set up the application"}</Text>
      <StatusBar style="auto" />
      {
        renderView()
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