import { setStatusBarBackgroundColor, setStatusBarNetworkActivityIndicatorVisible, StatusBar } from 'expo-status-bar';
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
} from 'react-native';
import { Button} from '@rneui/base';
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
const SET_NAME = 'SETUP_NAME'
const PHONE_SEND_CHANNEL = "group17/phone"
const PHONE_RECEIVE_CHANNEL = "group17/phoneCommand"
const CONNECT_DEVICE_MESSAGE = "SETUP_DEVICE"
const CONNECT_DEVICE_IR_READY = "IR_SETUP_READY"
const CONNECT_DEVICE_IR_DONE = "IR_SETUP_DONE"
const CONNECT_DEVICE_NAME_DONE = "NAME_SETUP_DONE"
const DEVICE_STATE_ON = "ON"
const DEVICE_STATE_OFF = "OFF"
const SENSE_ON = "SENSE_ON"
const SENSE_OFF = "SENSE_OFF"
const PHONE_ON = "PHONE_ON"
const PHONE_OFF = "PHONE_OFF"
const JSON_COMMAND_KEY = "command"
const JSON_NAME_KEY = "name"
const MESSAGE_ALERT = "ALERT"
const DEVICE_STATE_KEY = "DEVICE_KEY"
const ELECTRICITY_COST = 0.3182 // per kWh, as of Oct 2022
const AVERAGE_TV_WATTAGE = 0.060 // kW

var INIT_STATE = [
  {
    name: "TV",
    state: DEVICE_STATE_OFF,
    offTime: new Date(),
  },{
    name: "PAN",
    state: DEVICE_STATE_OFF,
    offTime: new Date(),
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

  async function detectDeviceOff(name) {
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

  async function detectDeviceOn(name) {
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

  async function addNewDevice(name) {
    console.log("Adding device")
    const currState = await retrieveData(DEVICE_STATE_KEY)
    currState.unshift({
      name: name,
      offTime: new Date(),
      state: DEVICE_STATE_OFF
    })

    console.log(currState)
    setAllDeviceState(currState)
    storeData(DEVICE_STATE_KEY, currState)
  }

  const onConnect = () => {
    console.log('onConnect');
    setStatus(CONNECTED)

    // subscribe to topic automatically
    subscribeTopic("HELLOWORLD")

    // subscribe to our actual endpoint
    subscribeTopic(PHONE_RECEIVE_CHANNEL)
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

    if (jsonMessage[JSON_COMMAND_KEY] === MESSAGE_ALERT) {
      playSound()
      stopSound()
    }

    if (jsonMessage[JSON_COMMAND_KEY] === CONNECT_DEVICE_IR_READY) {
      setStatus(ADDING_DEVICE)
    }

    if (jsonMessage[JSON_COMMAND_KEY] === CONNECT_DEVICE_IR_DONE) {
      // IR has been set up, now add name
      setDeviceName()
    }

    if (jsonMessage[JSON_COMMAND_KEY] === CONNECT_DEVICE_NAME_DONE) {
      // name has been added. Finish setting up new device and load from database
      finishSetup()
    }

    // things with name
    if (jsonMessage[JSON_COMMAND_KEY] === SENSE_ON) {
      detectDeviceOn(jsonMessage[JSON_NAME_KEY])
    } else if (jsonMessage[JSON_COMMAND_KEY] === SENSE_OFF) {
      detectDeviceOff(jsonMessage[JSON_NAME_KEY])
    }
  }

  const turnDeviceOn = (name) => {
    let jsonMessage = {
      command: PHONE_ON,
      name: name
    }

    sendMessage(jsonMessage, PHONE_SEND_CHANNEL)
    detectDeviceOn(name)
  }

  const turnDeviceOff = (name) => {
    let jsonMessage = {
      command: PHONE_OFF,
      name: name
    }

    sendMessage(jsonMessage, PHONE_SEND_CHANNEL)
    detectDeviceOff(name)
  }

  const subscribeTopic = (topicName) => {
    client.subscribe(topicName, { qos: 0 });
  }

  const sendMessage = (jsonMessage, topic) => {
    var mqttMessage = new Paho.MQTT.Message(JSON.stringify(jsonMessage));
    mqttMessage.destinationName = topic;
    client.send(mqttMessage);
  }

  // startConnectDevice
  const startConnectDevice = () => {
    // set state to fetching first to get that loading sign
    setStatus(FETCHING)

    // formulate message
    let jsonMessage = {
      command: CONNECT_DEVICE_MESSAGE
    }

    // send message to set up channel
    sendMessage(jsonMessage, PHONE_SEND_CHANNEL)
  }

  const setDeviceName = () => {
    // set state to fetching first to get that loading sign
    setStatus(SET_NAME)
  }

  const sendDeviceName = (deviceName) => {
    let jsonMessage = {
      command: SET_NAME,
      name: deviceName
    }
    sendMessage(jsonMessage, PHONE_SEND_CHANNEL)
    setStatus(FETCHING)
  }

  const finishSetup = () => {
    setStatus(CONNECTED)
    setDeviceNameInput("")
  }

  const calculateEnergySaving = (wattage, hours) => {
    return wattage * hours * ELECTRICITY_COST
  }

  const getHoursUntilAwake = (offTime) => {
    var nextAwake  = new Date();
    nextAwake.setDate(nextAwake.getDate() + 1)
    nextAwake.setHours(8);
    nextAwake.setMinutes(0);
    nextAwake.setMilliseconds(0);

    return (nextAwake - offTime) / 3600000
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
        <Text style={{ margin: 20 }}>{"Press DISCONNECT to turn off the application. Toggle your devices by tapping on their name."}</Text>
          {
            allDeviceState.map((device) => {
              if (device.state === DEVICE_STATE_ON) {
                return <Button 
                          type="clear"
                          key={device.name}
                          title={`Device name: ${device.name}. State: ON`} 
                          onPress={() => turnDeviceOff(device.name)}
                          buttonStyle={{ marginBottom:50 }}
                          titleStyle={{ color: 'black' }}
                        />
              } else {
                let offtime = new Date(device.offTime)
                return (
                  <View>
                    <Button
                      type='clear'
                      key={device.name}
                      title={`Device name: ${device.name}. State: Off since ${offtime.getHours()}:${offtime.getMinutes()}:${offtime.getSeconds()}`}
                      onPress={() => turnDeviceOn(device.name)}
                      buttonStyle={{ marginBottom:10 }}
                      titleStyle={{ color: 'black' }}
                    />
                    <Text style={{marginBottom: 10}}>{`You would have saved S$${calculateEnergySaving(AVERAGE_TV_WATTAGE, getHoursUntilAwake(offtime)).toFixed(2)} by 8am tomorrow!`}</Text>
                  </View>
                )
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
            buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
            onPress={startConnectDevice}
          />
          {
            sound
            ?
            <Button 
              type='solid'
              title='STOP ALARM'
              buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
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
          <Text style={{ margin: 20 }}>{"Please point your device's remote towards the receiver device and press the power button twice"}</Text>
          
          <Button
            type='solid'
            loading={true}
            disabled={true}
            buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
          />

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
          <Text style={{ margin: 20 }}>{"Input your new device's name"}</Text>
          <TextInput style={{ margin: 20 }}
            onChangeText={text => setDeviceNameInput(text)}
            placeholder={"Example: PanasonicTV"}
          />
          <Button
            type='solid'
            title='Submit device name'
            onPress={() => {
              // add device
              addNewDevice(deviceNameInput)
              sendDeviceName(deviceNameInput)
            }}
            buttonStyle={{ marginBottom:50, backgroundColor: '#397af8' }}
          />
        </View>
      )
    }

    if (status === FETCHING) {
      return (
        <Button
          type='solid'
          loading={true}
          disabled={true}
        />
      )
    }
    
    return (
      <View>
        <Text style={{ margin: 20 }}>{"Press CONNECT to set up the application."}</Text>
        <Button
          type='solid'
          title='CONNECT'
          onPress={connect}
          buttonStyle={{
            marginBottom:50,
            backgroundColor: status === 'failed' ? 'red' : '#397af8'
          }}
          icon={{ name: 'lan-connect', type: 'material-community', color: 'white' }}
        />
      </View>
      
    )
    
  }

  return (
    <View style={styles.container}>
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