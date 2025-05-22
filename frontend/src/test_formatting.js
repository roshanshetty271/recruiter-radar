import React from 'react';

const badComponent = ({ name, age }) => {
  const obj = { name: name, age: age };
  if (name) {
    console.log('Name exists');
  }
  return (
    <div>
      <p>Name:{name}</p>
      <p>Age:{age}</p>
    </div>
  );
};

export default badComponent;
