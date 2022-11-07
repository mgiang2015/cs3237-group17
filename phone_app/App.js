import { setStatusBarBackgroundColor, StatusBar } from 'expo-status-bar';
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
} from 'react-native';
import { Input, Button} from '@rneui/base';
import AsyncStorage from '@react-native-async-storage/async-storage';
import init from 'react_native_mqtt';
import { Audio } from 'expo-av';

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
const SET_NAME = 'SET_NAME'
const PHONE_CHANNEL = "group17/tvManager/phone"
const CONNECT_DEVICE_MESSAGE = "SETUP_DEVICE"
const CONNECT_DEVICE_IR_READY = "IR_SETUP_READY"
const CONNECT_DEVICE_IR_DONE = "IR_SETUP_DONE"
const CONNECT_DEVICE_NAME_DONE = "NAME_SETUP_DONE"
const DEVICE_STATE_ON = "ON"
const DEVICE_STATE_OFF = "OFF"
const JSON_MESSAGE_KEY = "command"
const MESSAGE_ALERT = "ALERT"
const DEVICE_STATE_KEY = "DEVICE_KEY"

var INIT_STATE = [
  {
    name: "TV",
    state: DEVICE_STATE_OFF,
    offTime: new Date(),
    irSignalOn: "ligma",
    irSignalOff: "ben dover",
  },{
    name: "PAN",
    state: DEVICE_STATE_OFF,
    offTime: new Date(),
    irSignalOn: "ligma",
    irSignalOff: "ben dover",
  }
]

export default function App() {
  const [status, setStatus] = useState(DISCONNECTED)
  const [allDeviceState, setAllDeviceState] = useState(INIT_STATE) // contains an array of device states, would be retrieved from database
  const [sound, setSound] = useState(null);
  const [deviceNameInput, setDeviceNameInput] = useState("");

  // AsyncStorage API
  // value is confirmed to be a JSON value
  const storeData = async (key, value) => {
    try {
      await AsyncStorage.setItem(
        key, JSON.stringify(value)
      );
    } catch (error) {
      console.log(error)
    }
  };
  
  const retrieveData = async (key) => {
    try {
      const value = await AsyncStorage.getItem(key);
      if (value !== null) {
        // We have data!!
        console.log(value);
        return JSON.parse(value)
      } else {
        return null
      }
    } catch (error) {
      console.log(error)
    }
  };
  
  async function playSound() {
    console.log('Loading Sound');
    // need to download a sound
    const { sound } = await Audio.Sound.createAsync(require('./hello.mp3'));
    setSound(sound);

    console.log('Playing Sound');
    await sound.playAsync();
  }

  function stopSound() {
    setSound(null)
  }

  async function turnOffDevice(name) {
    const currState = await retrieveData(DEVICE_STATE_KEY)
    if (currState) {
      const newState = currState.map(obj => {
        if (obj.name === name) {
          var clone = Object.assign({}, {...obj, state: DEVICE_STATE_OFF, offTime: new Date()})
          return clone
        }
  
        return {...obj};
      })
      console.log(newState)
      setAllDeviceState(newState)
      // save in asyncstorage too
      storeData(DEVICE_STATE_KEY, newState)
    }
    
  }

  async function turnOnDevice(name) {
    console.log("Retrieving data")
    const currState = await retrieveData(DEVICE_STATE_KEY)
    console.log(currState)
    if (currState) {
      const newState = currState.map(obj => {
        if (obj.name === name) {
          var clone = Object.assign({}, {...obj, state: DEVICE_STATE_ON})
          return clone
        }
  
        return {...obj};
      })
      console.log(newState)
      setAllDeviceState(newState)
      // save in asyncstorage too
      storeData(DEVICE_STATE_KEY, newState)
    }
  }

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
    setStatus(DISCONNECTED)
    client.disconnect()
    console.log("disconnected")
  }

  const onConnectionLost= (responseObject) => {
    if (status !== DISCONNECTED) {
      setStatus(DISCONNECTED)
    }

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

    if (jsonMessage[JSON_MESSAGE_KEY] === MESSAGE_ALERT) {
      playSound()
      stopSound()
    }

    if (jsonMessage[JSON_MESSAGE_KEY] === CONNECT_DEVICE_IR_READY) {
      setDeviceName(ADDING_DEVICE)
    }

    if (jsonMessage[JSON_MESSAGE_KEY] === CONNECT_DEVICE_IR_DONE) {
      // IR has been set up, now add name
      setDeviceName()
    }

    if (jsonMessage[JSON_MESSAGE_KEY] === CONNECT_DEVICE_NAME_DONE) {
      // name has been added. Finish setting up new device and load from database
      finishSetup()
    }

    // handle turning off and on device. deviceCommand[0] is name, [1] is ON / OFF
    const deviceCommand = jsonMessage[JSON_MESSAGE_KEY].split('_')
    if (deviceCommand[1] === DEVICE_STATE_ON) {
      turnOnDevice(deviceCommand[0])
    } else if (deviceCommand[1] === DEVICE_STATE_OFF) {
      turnOffDevice(deviceCommand[0])
    }
  }

  const subscribeTopic = (topicName) => {
    client.subscribe(topicName, { qos: 0 });
  }

  const unsubscribeTopic = (topicName) => {
    client.unsubscribe(topicName);
  }

  const sendMessage = (message, topic) => {
    var mqttMessage = new Paho.MQTT.Message(`{"${JSON_MESSAGE_KEY}":"${message}"}`);
    mqttMessage.destinationName = topic;
    client.send(mqttMessage);
  }

  // startConnectDevice
  const startConnectDevice = () => {
    // set state to fetching first to get that loading sign
    setStatus(FETCHING)

    // send message to set up channel
    sendMessage(CONNECT_DEVICE_MESSAGE, PHONE_CHANNEL)
  }

  const setDeviceName = () => {
    // set state to fetching first to get that loading sign
    setStatus(SET_NAME)
  }

  const sendDeviceName = (deviceName) => {
    let message = `SETUP_NAME_${deviceName}`
    sendMessage(message, PHONE_CHANNEL)
    setStatus(FETCHING)
  }

  const finishSetup = () => {
    setStatus(CONNECTED)
  }

  // set up async storage
  useEffect(() => {
    async function storeInitState() {
      await storeData(DEVICE_STATE_KEY, INIT_STATE)
      let val = await retrieveData(DEVICE_STATE_KEY)
    }

    storeInitState()
  }, [])

  // set up client
  useEffect(() => {
    setStatus(DISCONNECTED)
    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
  }, [client])

  // set up sound
  useEffect(() => {
    return sound
      ? () => {
          console.log('Unloading Sound');
          // unloadAsync to prevent memory leaks
          sound.unloadAsync();
        }
      : undefined;
  }, [sound]);


  // Button renderer
  const renderView = () => {
    // connected and TV is on
    if (status === CONNECTED) {
      return (
        <View>
          {
            allDeviceState.map((device) => {
              if (device.state === DEVICE_STATE_ON) {
                return <Text key={device.name}>{`Device name: ${device.name}. State: ON`}</Text>
              } else {
                let date = new Date(device.offTime)
                return <Text key={device.name}>{`Device name: ${device.name}. State: Off since ${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`}</Text>
              }
            })
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
          {
            sound
            ?
            <Button 
              type='solid'
              title='STOP ALARM'
              onPress={stopSound}
            />
            : null
          }
        </View>
      )
    }

    if (status === ADDING_DEVICE) {
      return (
        <View>
          <Text>{"Please point your device's remote towards the receiver device and press the power button twice"}</Text>
          <Button
              type='solid'
              title='STOP SET UP'
              onPress={() => setStatus(CONNECTED)}
              buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
            />
        </View>
      )
    }

    if (status === SET_NAME) {
      return (
        <View>
          <Text>{"Input your new device's name (no underscore please)"}</Text>
          <TextInput 
            onChangeText={text => setDeviceNameInput(text)}
            placeholder={"Example: PanasonicTV"}
          />
          <Button
            type='solid'
            title='Submit device name'
            onPress={() => sendDeviceName(deviceNameInput)}
            buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
          />
        </View>
      )
    }
    
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